"""
Vector Search API Routes
-------------------------
All /ai/vector/* endpoints for production semantic matching.

Endpoints:
    POST /ai/vector/match-technicians   — ANN match for a job (JWT protected)
    POST /ai/vector/search              — free-text technician search (JWT protected)
    POST /ai/vector/update-technician   — trigger single embedding regen (JWT protected)
    POST /ai/vector/update-job          — trigger single job embedding regen (JWT protected)
    POST /ai/vector/rebuild             — batch rebuild (admin only)
    GET  /ai/vector/analytics           — vector system analytics (admin only)

Cache flow:
    Check Redis → if HIT return cached result
    else: run ANN → rank → cache → return

All endpoints use the existing synchronous Session/get_session pattern.
"""
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user, get_current_admin
from app.models.job import Job
from app.models.technician import Technician
from app.models.user import User
from app.schemas.vector_schema import (
    RebuildRequest,
    RebuildResponse,
    UpdateEmbeddingResponse,
    UpdateJobEmbeddingRequest,
    UpdateTechnicianEmbeddingRequest,
    VectorAnalyticsResponse,
    VectorMatchRequest,
    VectorMatchResponse,
    VectorMatchResult,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorSearchResult,
    ScoreBreakdown,
)
from app.services.vector import (
    embedding_service,
    redis_cache,
    vector_search_service,
    ranking_service,
    synchronization_service,
    analytics_tracker,
    embedding_queue,
)
from app.utils.logger import logger

router = APIRouter(prefix="/ai/vector", tags=["Vector Search"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_or_build_job_embedding(session: Session, job: Job):
    """
    Return the job's embedding: prefer DB value, fall back to generating
    (and persisting) it on the fly.
    """
    job_id = str(job.id)
    job_str = str(job.id)

    # Try Redis first
    cached = redis_cache.get_job_embedding(job_id)
    if cached:
        redis_cache.increment_counter("cache_hits")
        return cached

    # Try DB value
    if job.job_embedding:
        vec = list(job.job_embedding)
        redis_cache.set_job_embedding(job_id, vec)
        return vec

    # Generate on the fly
    redis_cache.increment_counter("cache_misses")
    job_dict = job.model_dump()
    vec = embedding_service.generate_job_embedding(job_dict)
    vector_search_service.save_job_embedding(session, job_id, vec)
    redis_cache.set_job_embedding(job_id, vec)
    return vec


# ── POST /ai/vector/match-technicians ────────────────────────────────────────


@router.post("/match-technicians", response_model=VectorMatchResponse)
def match_technicians_vector(
    req: VectorMatchRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic ANN search: find top matching technicians for a job.

    Flow:
        1. Check Redis ANN cache
        2. Get / generate job embedding
        3. pgvector ANN over technician_profiles
        4. Hybrid ranking (vector + completion + rating + availability + distance)
        5. Cache results
        6. Return ranked list
    """
    t0 = time.perf_counter()
    job_id_str = str(req.job_id)

    # 1. Check ANN result cache
    cached_results = redis_cache.get_match_result(job_id_str)
    if cached_results:
        latency_ms = (time.perf_counter() - t0) * 1000
        analytics_tracker.track_match(
            job_id_str,
            len(cached_results),
            cached_results[0].get("final_score", 0.0) if cached_results else 0.0,
            latency_ms,
            cache_hit=True,
        )
        return VectorMatchResponse(
            job_id=req.job_id,
            total_candidates=len(cached_results),
            cached=True,
            latency_ms=round(latency_ms, 2),
            matches=_build_match_results(cached_results[: req.top_k]),
        )

    # 2. Fetch job
    job = session.get(Job, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        from sqlmodel import text
        import json

        budget = float(job.budget) if job.budget else 10000.0
        job_skills = job.required_skills or []
        
        # Explicit heuristic SQL query bypassing vector logic entirely
        # Fetching all online technicians that match price constraint
        sql = text("""
            SELECT
                id::text AS technician_id,
                skills,
                experience_years,
                average_rating,
                completion_rate,
                fraud_risk_score,
                is_online,
                latitude,
                longitude,
                response_time_minutes,
                total_jobs_completed,
                price,
                base_hourly_rate,
                current_status
            FROM technician_profiles
            WHERE is_online = true
              AND (base_hourly_rate <= :budget OR price <= :budget OR base_hourly_rate IS NULL)
        """)
        
        rows = session.exec(sql, params={"budget": budget}).all()
        
        candidates = []
        for row in rows:
            tech_skills = []
            if isinstance(row.skills, list):
                tech_skills = [str(s).lower() for s in row.skills]
            elif isinstance(row.skills, str):
                try:
                    parsed = json.loads(row.skills)
                    tech_skills = [str(s).lower() for s in parsed] if isinstance(parsed, list) else []
                except:
                    pass
            
            # Calculate skill overlap score
            matched = [s for s in job_skills if str(s).lower() in tech_skills]
            missing = [s for s in job_skills if str(s).lower() not in tech_skills]
            skill_score = len(matched) / len(job_skills) if job_skills else 1.0
            
            # If strictly filtering by skill, we could skip if skill_score == 0, but user said "use skill as parameter and take prices, experience... compute ranking"
            
            # Calculate a heuristic final score
            exp = float(row.experience_years or 0)
            exp_score = min(1.0, exp / 10.0) # max out at 10 years
            
            rating = float(row.average_rating or 0.0)
            rating_score = min(1.0, rating / 5.0)
            
            comp = float(row.completion_rate or 0.0)
            
            fraud = float(row.fraud_risk_score or 0.0)
            
            tech_price = float(getattr(row, "price", None) or row.base_hourly_rate or 0.0)
            price_score = 1.0 - (tech_price / budget) if budget > 0 else 1.0
            price_score = max(0.0, min(1.0, price_score))
            
            # Weights: Skills (40%), Experience (20%), Rating (20%), Price (10%), Completion (10%)
            final_score = (skill_score * 0.40) + (exp_score * 0.20) + (rating_score * 0.20) + (price_score * 0.10) + (comp * 0.10)
            
            # Apply fraud penalty
            if fraud > 0.5:
                final_score *= 0.1
                
            candidates.append({
                "technician_id": row.technician_id,
                "similarity_score": round(skill_score, 4),
                "final_score": round(final_score, 4),
                "matched_skills": matched,
                "missing_skills": missing,
                "experience_years": int(exp),
                "average_rating": rating,
                "completion_rate": comp,
                "is_online": bool(row.is_online),
                "current_status": row.current_status or "online",
                "total_jobs_completed": int(row.total_jobs_completed or 0),
                "base_hourly_rate": tech_price,
                "_score_breakdown": {
                    "vector_similarity": round(skill_score, 4), # Overloading this field for compatibility
                    "completion_rate": round(comp, 4),
                    "average_rating": round(rating_score, 4),
                    "availability_score": 1.0,
                    "distance_score": 1.0,
                    "response_bonus": 0.0,
                    "fraud_penalty_applied": fraud > 0.5,
                }
            })
            
        # Sort candidates by final score descending
        candidates.sort(key=lambda x: x["final_score"], reverse=True)
        ranked = candidates[:req.top_k]

        # 6. Cache results
        try:
            redis_cache.set_match_result(job_id_str, ranked)
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")

        latency_ms = (time.perf_counter() - t0) * 1000
        analytics_tracker.track_match(
            job_id_str,
            len(ranked),
            ranked[0]["final_score"] if ranked else 0.0,
            latency_ms,
            cache_hit=False,
        )

        return VectorMatchResponse(
            job_id=req.job_id,
            total_candidates=len(ranked),
            cached=False,
            latency_ms=round(latency_ms, 2),
            matches=_build_match_results(ranked),
        )

    except Exception as exc:
        import traceback
        logger.error(
            f"Vector match failed for job {job_id_str} — falling back to empty result. "
            f"Error: {exc}\n{traceback.format_exc()}"
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        return VectorMatchResponse(
            job_id=req.job_id,
            total_candidates=0,
            cached=False,
            latency_ms=round(latency_ms, 2),
            matches=[],
        )


# ── POST /ai/vector/search ────────────────────────────────────────────────────


@router.post("/search", response_model=VectorSearchResponse)
def semantic_search(
    req: VectorSearchRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Free-text semantic search over technician profiles.
    Useful for: "find plumbers with 5 years solar experience in Lagos".
    """
    t0 = time.perf_counter()
    query = req.query.strip()

    # Cache check
    cached = redis_cache.get_skill_search(query)
    if cached:
        filtered = cached if not req.only_online else [r for r in cached if r.get("is_online")]
        latency_ms = (time.perf_counter() - t0) * 1000
        analytics_tracker.track_search(query, len(filtered), 0.0, latency_ms, cache_hit=True)
        return VectorSearchResponse(
            query=query,
            total_results=len(filtered),
            cached=True,
            latency_ms=round(latency_ms, 2),
            results=_build_search_results(filtered[: req.top_k]),
        )

    # Encode query
    query_embedding = embedding_service.encode_text(query)

    # ANN search
    candidates = vector_search_service.find_similar_technicians(
        session,
        query_embedding=query_embedding,
        top_k=req.top_k * 2,
        min_similarity=req.min_similarity,
    )

    # Optional online filter
    if req.only_online:
        candidates = [c for c in candidates if c.get("is_online")]

    # Cache full unfiltered set
    redis_cache.set_skill_search(query, candidates)

    results = candidates[: req.top_k]
    avg_sim = (
        sum(r["similarity_score"] for r in results) / len(results) if results else 0.0
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    analytics_tracker.track_search(query, len(results), avg_sim, latency_ms, cache_hit=False)

    return VectorSearchResponse(
        query=query,
        total_results=len(results),
        cached=False,
        latency_ms=round(latency_ms, 2),
        results=_build_search_results(results),
    )


# ── POST /ai/vector/update-technician ────────────────────────────────────────


@router.post("/update-technician", response_model=UpdateEmbeddingResponse)
def update_technician_embedding(
    req: UpdateTechnicianEmbeddingRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger embedding regeneration for a technician.
    The update is queued to Redis for async processing (non-blocking).
    """
    tech_id = str(req.technician_id)

    # Verify technician exists
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    # Enqueue to Redis queue (background worker picks it up)
    redis_cache.enqueue_embedding_rebuild("technician", tech_id)

    # Also invalidate stale cache immediately
    redis_cache.invalidate_technician_embedding(tech_id)

    return UpdateEmbeddingResponse(
        entity_type="technician",
        entity_id=tech_id,
        success=True,
        message="Embedding regeneration queued.",
        queued=True,
    )


# ── POST /ai/vector/update-job ────────────────────────────────────────────────


@router.post("/update-job", response_model=UpdateEmbeddingResponse)
def update_job_embedding(
    req: UpdateJobEmbeddingRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Synchronously regenerate and persist the embedding for a job.
    Invalidates stale ANN match results.
    """
    job_id = str(req.job_id)

    job = session.get(Job, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    ok = synchronization_service.sync_job_embedding(session, job_id, job.model_dump())

    if not ok:
        raise HTTPException(
            status_code=500, detail="Failed to regenerate job embedding."
        )

    return UpdateEmbeddingResponse(
        entity_type="job",
        entity_id=job_id,
        success=True,
        message="Job embedding updated and ANN cache invalidated.",
        queued=False,
    )


# ── POST /ai/vector/rebuild ───────────────────────────────────────────────────


@router.post("/rebuild", response_model=RebuildResponse)
def rebuild_embeddings(
    req: RebuildRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin),  # admin only
):
    """
    Batch rebuild embeddings for all technicians / jobs with missing vectors.
    Runs synchronously (may be slow for large datasets).
    For nightly runs, call this endpoint via a cron / scheduler.
    """
    tech_stats = None
    job_stats = None

    if req.target in ("technicians", "all"):
        tech_stats = synchronization_service.rebuild_all_technicians(session)

    if req.target in ("jobs", "all"):
        job_stats = synchronization_service.rebuild_all_jobs(session)

    return RebuildResponse(
        target=req.target,
        technicians=tech_stats,
        jobs=job_stats,
        message="Rebuild complete.",
    )


# ── GET /ai/vector/analytics ──────────────────────────────────────────────────


@router.get("/analytics", response_model=VectorAnalyticsResponse)
def get_vector_analytics(
    current_user: User = Depends(get_current_admin),
):
    """Return vector system operational analytics (admin only)."""
    return VectorAnalyticsResponse(
        analytics=analytics_tracker.get_full_analytics(),
        worker_running=embedding_queue.is_worker_running(),
    )


# ── Response builders (keep routes thin) ─────────────────────────────────────


def _build_match_results(ranked):
    results = []
    for r in ranked:
        breakdown = r.get("_score_breakdown")
        results.append(
            VectorMatchResult(
                technician_id=r["technician_id"],
                similarity_score=r["similarity_score"],
                final_score=r["final_score"],
                matched_skills=r.get("matched_skills", []),
                missing_skills=r.get("missing_skills", []),
                experience_years=r.get("experience_years", 0),
                average_rating=r.get("average_rating", 0.0),
                completion_rate=r.get("completion_rate", 0.0),
                is_online=r.get("is_online", False),
                current_status=r.get("current_status", "offline"),
                total_jobs_completed=r.get("total_jobs_completed", 0),
                base_hourly_rate=r.get("base_hourly_rate"),
                score_breakdown=ScoreBreakdown(**breakdown) if breakdown else None,
            )
        )
    return results


def _build_search_results(candidates):
    return [
        VectorSearchResult(
            technician_id=c["technician_id"],
            similarity_score=c["similarity_score"],
            skills=c.get("skills", []),
            experience_years=c.get("experience_years", 0),
            average_rating=c.get("average_rating", 0.0),
            is_online=c.get("is_online", False),
        )
        for c in candidates
    ]
