"""
Redis Cache Layer for Vector Services
--------------------------------------
Provides a lazily-initialised Redis client (connection pool) and all
cache get/set/invalidate helpers used by the vector layer.

Key schema:
    technician_embedding:{technician_id}  → JSON list[float]  (TTL: VECTOR_CACHE_TTL)
    job_embedding:{job_id}                → JSON list[float]  (TTL: VECTOR_CACHE_TTL)
    vector_match:{job_id}                 → JSON match result (TTL: SEARCH_CACHE_TTL)
    skill_search:{query_hash}             → JSON result list  (TTL: SEARCH_CACHE_TTL)
    top_technicians:{skill}               → JSON result list  (TTL: SEARCH_CACHE_TTL)
    vector_analytics:*                    → counters/hashes
"""
from __future__ import annotations

import hashlib
import json
import time
import threading
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.utils.logger import logger

# ── Client singleton ──────────────────────────────────────────────────────────

_redis_client = None
_redis_lock = threading.Lock()


def get_redis():
    """
    Return a shared Redis connection pool client.
    Returns None if REDIS_URL is not configured (graceful degradation).
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    with _redis_lock:
        if _redis_client is not None:
            return _redis_client

        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not configured — vector caching disabled.")
            return None

        try:
            import redis as redis_lib  # type: ignore

            _redis_client = redis_lib.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                # Keep short so idle sockets don't exceed Redis Cloud limits
                socket_timeout=3,
                socket_keepalive=True,
                retry_on_timeout=True,
                max_connections=20,
                health_check_interval=30,  # periodic ping to keep connection alive
            )
            # Confirm connectivity
            _redis_client.ping()
            logger.info("Redis connection established (vector cache).")
        except Exception as exc:
            logger.error(f"Redis connection failed: {exc}")
            _redis_client = None  # stay None — callers handle gracefully

    return _redis_client


# ── Key helpers ───────────────────────────────────────────────────────────────


def _tech_embed_key(tech_id: str) -> str:
    return f"technician_embedding:{tech_id}"


def _job_embed_key(job_id: str) -> str:
    return f"job_embedding:{job_id}"


def _match_key(job_id: str) -> str:
    return f"vector_match:{job_id}"


def _skill_search_key(query: str) -> str:
    digest = hashlib.md5(query.lower().strip().encode()).hexdigest()
    return f"skill_search:{digest}"


def _top_tech_key(skill: str) -> str:
    return f"top_technicians:{skill.lower().strip()}"


# ── Technician embedding cache ────────────────────────────────────────────────


def get_technician_embedding(tech_id: str) -> Optional[List[float]]:
    """Return cached embedding or None on miss/error."""
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(_tech_embed_key(tech_id))
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning(f"Redis get technician_embedding failed: {exc}")
    return None


def set_technician_embedding(tech_id: str, embedding: List[float]) -> None:
    """Persist technician embedding with TTL."""
    r = get_redis()
    if not r:
        return
    try:
        r.setex(
            _tech_embed_key(tech_id),
            settings.VECTOR_CACHE_TTL,
            json.dumps(embedding),
        )
    except Exception as exc:
        logger.warning(f"Redis set technician_embedding failed: {exc}")


def invalidate_technician_embedding(tech_id: str) -> None:
    """Delete cached embedding (call when technician data changes)."""
    r = get_redis()
    if not r:
        return
    try:
        r.delete(_tech_embed_key(tech_id))
        logger.info(f"Invalidated embedding cache for technician {tech_id}")
    except Exception as exc:
        logger.warning(f"Redis delete technician_embedding failed: {exc}")


# ── Job embedding cache ───────────────────────────────────────────────────────


def get_job_embedding(job_id: str) -> Optional[List[float]]:
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(_job_embed_key(job_id))
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning(f"Redis get job_embedding failed: {exc}")
    return None


def set_job_embedding(job_id: str, embedding: List[float]) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.setex(
            _job_embed_key(job_id),
            settings.VECTOR_CACHE_TTL,
            json.dumps(embedding),
        )
    except Exception as exc:
        logger.warning(f"Redis set job_embedding failed: {exc}")


def invalidate_job_embedding(job_id: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.delete(_job_embed_key(job_id))
        logger.info(f"Invalidated embedding cache for job {job_id}")
    except Exception as exc:
        logger.warning(f"Redis delete job_embedding failed: {exc}")


# ── ANN match result cache ────────────────────────────────────────────────────


def get_match_result(job_id: str) -> Optional[List[Dict[str, Any]]]:
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(_match_key(job_id))
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning(f"Redis get vector_match failed: {exc}")
    return None


def set_match_result(job_id: str, results: List[Dict[str, Any]]) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.setex(
            _match_key(job_id),
            settings.SEARCH_CACHE_TTL,
            json.dumps(results),
        )
    except Exception as exc:
        logger.warning(f"Redis set vector_match failed: {exc}")


def invalidate_match_result(job_id: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.delete(_match_key(job_id))
    except Exception as exc:
        logger.warning(f"Redis delete vector_match failed: {exc}")


# ── Skill search cache ────────────────────────────────────────────────────────


def get_skill_search(query: str) -> Optional[List[Dict[str, Any]]]:
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(_skill_search_key(query))
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning(f"Redis get skill_search failed: {exc}")
    return None


def set_skill_search(query: str, results: List[Dict[str, Any]]) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.setex(
            _skill_search_key(query),
            settings.SEARCH_CACHE_TTL,
            json.dumps(results),
        )
    except Exception as exc:
        logger.warning(f"Redis set skill_search failed: {exc}")


# ── Top technicians per skill cache ──────────────────────────────────────────


def get_top_technicians(skill: str) -> Optional[List[Dict[str, Any]]]:
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(_top_tech_key(skill))
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning(f"Redis get top_technicians failed: {exc}")
    return None


def set_top_technicians(skill: str, results: List[Dict[str, Any]]) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.setex(
            _top_tech_key(skill),
            settings.SEARCH_CACHE_TTL,
            json.dumps(results),
        )
    except Exception as exc:
        logger.warning(f"Redis set top_technicians failed: {exc}")


# ── Embedding rebuild queue (Redis list used as a simple job queue) ───────────


def enqueue_embedding_rebuild(entity_type: str, entity_id: str) -> None:
    """
    Push a rebuild task onto the Redis list queue.
    entity_type: "technician" | "job"
    """
    r = get_redis()
    if not r:
        logger.warning(
            f"Redis unavailable — skipping enqueue for {entity_type}:{entity_id}"
        )
        return
    try:
        payload = json.dumps({"type": entity_type, "id": entity_id})
        r.rpush(settings.EMBEDDING_QUEUE_KEY, payload)
        logger.info(f"Enqueued embedding rebuild: {entity_type}:{entity_id}")
    except Exception as exc:
        logger.warning(f"Redis enqueue failed: {exc}")


def dequeue_embedding_rebuild() -> Optional[Dict[str, str]]:
    """
    Non-blocking pop from the rebuild queue. Returns None if queue is empty.

    Uses LPOP (non-blocking) instead of BLPOP to avoid holding an idle TCP
    connection longer than Redis Cloud's connection timeout (~5-10 s).
    The caller (worker loop) sleeps between polls.
    """
    r = get_redis()
    if not r:
        return None
    try:
        payload = r.lpop(settings.EMBEDDING_QUEUE_KEY)
        if payload:
            return json.loads(payload)
    except Exception as exc:
        logger.warning(f"Redis dequeue failed: {exc}")
    return None


# ── Analytics counters ────────────────────────────────────────────────────────


def increment_counter(key: str, amount: int = 1) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.incrby(f"vector_analytics:{key}", amount)
    except Exception:
        pass


def record_latency(operation: str, elapsed_ms: float) -> None:
    """
    Maintain a rolling average latency per operation using a Redis hash.
    Hash: vector_analytics:latency
    Fields: {operation}_total_ms, {operation}_count
    """
    r = get_redis()
    if not r:
        return
    try:
        pipe = r.pipeline()
        pipe.hincrbyfloat("vector_analytics:latency", f"{operation}_total_ms", elapsed_ms)
        pipe.hincrby("vector_analytics:latency", f"{operation}_count", 1)
        pipe.execute()
    except Exception:
        pass


def get_analytics_snapshot() -> Dict[str, Any]:
    """Return all vector analytics counters as a dict."""
    r = get_redis()
    if not r:
        return {}
    try:
        raw_counters = r.hgetall("vector_analytics:latency") or {}
        # Reconstruct averages
        result: Dict[str, Any] = {}
        ops = set()
        for k in raw_counters:
            op = k.replace("_total_ms", "").replace("_count", "")
            ops.add(op)
        for op in ops:
            total = float(raw_counters.get(f"{op}_total_ms", 0))
            count = int(raw_counters.get(f"{op}_count", 0) or 1)
            result[f"{op}_avg_ms"] = round(total / count, 2)
            result[f"{op}_count"] = count

        # Simple counters
        for k in ["cache_hits", "cache_misses", "embed_generated", "ann_queries"]:
            val = r.get(f"vector_analytics:{k}")
            if val:
                result[k] = int(val)
        return result
    except Exception as exc:
        logger.warning(f"Redis get_analytics_snapshot failed: {exc}")
        return {}
