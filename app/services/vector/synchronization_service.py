"""
Embedding Synchronization Service
-----------------------------------
Called by the vector routes and the background queue worker whenever
technician or job data changes and embeddings need to be regenerated.

Design:
- sync_technician_embedding  → single technician regen + Redis update
- sync_job_embedding         → single job regen + Redis update
- rebuild_all_technicians    → full batch rebuild (called nightly or on demand)
- rebuild_all_jobs           → full batch rebuild

These functions use the existing synchronous SQLModel session pattern.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from app.services.vector import embedding_service, redis_cache, vector_search_service
from app.utils.logger import logger


# ── Single technician sync ────────────────────────────────────────────────────


def sync_technician_embedding(
    session: Session,
    technician_id: str,
    tech_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Regenerate and persist the embedding for a single technician.

    If `tech_data` is provided (e.g. dict from model_dump()), it is used
    directly; otherwise the DB is queried.

    Steps:
        1. Build profile text
        2. Encode with SentenceTransformer
        3. Persist to DB (UPDATE)
        4. Update Redis cache
        5. Invalidate stale ANN search caches
    """
    t0 = time.perf_counter()

    try:
        # Fetch from DB if not provided
        if tech_data is None:
            from sqlmodel import text

            row = session.exec(
                text(
                    """
                    SELECT id::text, skills, experience_years, average_rating,
                           completion_rate, bio, education, languages,
                           work_history, preferred_work_types, verification_level,
                           total_jobs_completed, role, industry
                    FROM technician_profiles
                    WHERE id = :tech_id
                    LIMIT 1
                    """
                ),
                params={"tech_id": technician_id},
            ).first()

            if not row:
                logger.warning(f"Technician {technician_id} not found for embedding sync.")
                return False

            tech_data = dict(row._mapping)

        # Generate embedding
        embedding = embedding_service.generate_technician_embedding(tech_data)
        redis_cache.increment_counter("embed_generated")

        # Persist to DB
        ok = vector_search_service.save_technician_embedding(
            session, technician_id, embedding
        )
        if not ok:
            return False

        # Update Redis embedding cache
        redis_cache.set_technician_embedding(technician_id, embedding)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        redis_cache.record_latency("sync_technician", elapsed_ms)
        logger.info(
            f"Synced technician {technician_id} embedding in {elapsed_ms:.1f}ms"
        )
        return True

    except Exception as exc:
        logger.error(f"sync_technician_embedding failed for {technician_id}: {exc}")
        return False


# ── Single job sync ───────────────────────────────────────────────────────────


def sync_job_embedding(
    session: Session,
    job_id: str,
    job_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Regenerate and persist the embedding for a single job.
    Also invalidates the ANN match result cache for this job.
    """
    t0 = time.perf_counter()

    try:
        if job_data is None:
            from sqlmodel import text

            row = session.exec(
                text(
                    """
                    SELECT id::text, title, description, required_skills, urgency_level
                    FROM job_requests
                    WHERE id = :job_id
                    LIMIT 1
                    """
                ),
                params={"job_id": job_id},
            ).first()

            if not row:
                logger.warning(f"Job {job_id} not found for embedding sync.")
                return False

            job_data = dict(row._mapping)

        # Generate embedding
        embedding = embedding_service.generate_job_embedding(job_data)
        redis_cache.increment_counter("embed_generated")

        # Persist to DB
        ok = vector_search_service.save_job_embedding(session, job_id, embedding)
        if not ok:
            return False

        # Update Redis caches
        redis_cache.set_job_embedding(job_id, embedding)
        redis_cache.invalidate_match_result(job_id)  # stale ANN results

        elapsed_ms = (time.perf_counter() - t0) * 1000
        redis_cache.record_latency("sync_job", elapsed_ms)
        logger.info(f"Synced job {job_id} embedding in {elapsed_ms:.1f}ms")
        return True

    except Exception as exc:
        logger.error(f"sync_job_embedding failed for {job_id}: {exc}")
        return False


# ── Full rebuild ──────────────────────────────────────────────────────────────


def rebuild_all_technicians(session: Session, batch_size: int = 50) -> Dict[str, int]:
    """
    Batch-encode ALL technicians missing embeddings.

    Returns:
        {"processed": int, "succeeded": int, "failed": int}
    """
    logger.info("Starting full technician embedding rebuild...")
    total_processed = 0
    total_succeeded = 0
    total_failed = 0

    while True:
        batch = vector_search_service.get_technicians_missing_embeddings(
            session, limit=batch_size
        )
        if not batch:
            break

        ids = [row["id"] for row in batch]
        texts = [embedding_service.build_technician_profile_text(row) for row in batch]
        vectors = embedding_service.encode_batch(texts)

        for row, vec in zip(batch, vectors):
            tech_id = row["id"]
            ok = vector_search_service.save_technician_embedding(session, tech_id, vec)
            if ok:
                redis_cache.set_technician_embedding(tech_id, vec)
                total_succeeded += 1
            else:
                total_failed += 1
            total_processed += 1

        logger.info(
            f"Rebuild progress: {total_processed} processed, "
            f"{total_succeeded} ok, {total_failed} failed"
        )

    logger.info(
        f"Technician rebuild complete: {total_succeeded}/{total_processed} succeeded."
    )
    return {
        "processed": total_processed,
        "succeeded": total_succeeded,
        "failed": total_failed,
    }


def rebuild_all_jobs(session: Session, batch_size: int = 50) -> Dict[str, int]:
    """
    Batch-encode ALL jobs missing embeddings.
    """
    logger.info("Starting full job embedding rebuild...")
    total_processed = 0
    total_succeeded = 0
    total_failed = 0

    while True:
        batch = vector_search_service.get_jobs_missing_embeddings(
            session, limit=batch_size
        )
        if not batch:
            break

        texts = [embedding_service.build_job_profile_text(row) for row in batch]
        vectors = embedding_service.encode_batch(texts)

        for row, vec in zip(batch, vectors):
            job_id = row["id"]
            ok = vector_search_service.save_job_embedding(session, job_id, vec)
            if ok:
                redis_cache.set_job_embedding(job_id, vec)
                redis_cache.invalidate_match_result(job_id)
                total_succeeded += 1
            else:
                total_failed += 1
            total_processed += 1

    logger.info(
        f"Job rebuild complete: {total_succeeded}/{total_processed} succeeded."
    )
    return {
        "processed": total_processed,
        "succeeded": total_succeeded,
        "failed": total_failed,
    }
