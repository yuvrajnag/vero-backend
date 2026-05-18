"""
Vector Analytics Tracker
-------------------------
Lightweight tracker for vector search operational metrics.
All data is stored in Redis (see redis_cache) and optionally persisted
to the existing platform_metrics table.

Tracked metrics:
    - ANN query latency (avg / p95 approximation)
    - Cache hit/miss rate
    - Embedding generation count & duration
    - Most-searched skills
    - Match quality (avg similarity score returned)
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from app.services.vector import redis_cache
from app.utils.logger import logger


def track_search(
    query_text: str,
    top_k_returned: int,
    avg_similarity: float,
    latency_ms: float,
    cache_hit: bool,
) -> None:
    """Record a vector search event."""
    try:
        redis_cache.record_latency("vector_search", latency_ms)
        if cache_hit:
            redis_cache.increment_counter("cache_hits")
        else:
            redis_cache.increment_counter("cache_misses")

        redis_cache.increment_counter("total_searches")

        # Track most-searched terms (simple Redis sorted set)
        r = redis_cache.get_redis()
        if r and query_text:
            r.zincrby("vector_analytics:search_terms", 1, query_text[:200])

        logger.info(
            f"Vector search tracked: latency={latency_ms:.1f}ms "
            f"cache_hit={cache_hit} avg_sim={avg_similarity:.3f}"
        )
    except Exception as exc:
        logger.warning(f"track_search failed (non-fatal): {exc}")


def track_match(
    job_id: str,
    candidates_returned: int,
    top_similarity: float,
    latency_ms: float,
    cache_hit: bool,
) -> None:
    """Record a technician match event."""
    try:
        redis_cache.record_latency("match_technicians", latency_ms)
        redis_cache.increment_counter("total_matches")
        if cache_hit:
            redis_cache.increment_counter("cache_hits")
        else:
            redis_cache.increment_counter("cache_misses")

        r = redis_cache.get_redis()
        if r and top_similarity > 0:
            r.hincrbyfloat("vector_analytics:match_quality", "total_similarity", top_similarity)
            r.hincrby("vector_analytics:match_quality", "count", 1)
    except Exception as exc:
        logger.warning(f"track_match failed (non-fatal): {exc}")


def get_top_searched_skills(limit: int = 20) -> List[Dict[str, Any]]:
    """Return most-searched terms from the sorted set."""
    r = redis_cache.get_redis()
    if not r:
        return []
    try:
        raw = r.zrevrange("vector_analytics:search_terms", 0, limit - 1, withscores=True)
        return [{"skill": term, "count": int(score)} for term, score in raw]
    except Exception as exc:
        logger.warning(f"get_top_searched_skills failed: {exc}")
        return []


def get_full_analytics() -> Dict[str, Any]:
    """Aggregate all vector analytics into a single response dict."""
    base = redis_cache.get_analytics_snapshot()

    # Cache hit rate
    hits = int(base.get("cache_hits", 0))
    misses = int(base.get("cache_misses", 0))
    total = hits + misses
    base["cache_hit_rate"] = round(hits / total, 4) if total > 0 else 0.0

    # Match quality
    r = redis_cache.get_redis()
    if r:
        try:
            mq = r.hgetall("vector_analytics:match_quality") or {}
            total_sim = float(mq.get("total_similarity", 0))
            count = int(mq.get("count", 0) or 1)
            base["avg_match_similarity"] = round(total_sim / count, 4)
        except Exception:
            pass

    base["top_searched_skills"] = get_top_searched_skills(10)
    return base
