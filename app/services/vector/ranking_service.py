"""
Hybrid Ranking Engine
----------------------
Combines vector similarity with operational signals to produce a final
ranked score for each technician candidate.

Default formula weights:
    vector_similarity   → 0.55
    completion_rate     → 0.20
    average_rating      → 0.15
    availability_score  → 0.05
    distance_score      → 0.05

All weights must sum to 1.0.  Override via `weights` parameter.

Fraud penalty: technicians with fraud_risk_score >= 0.70 are capped at
final_score = 0.1 (still returned so the caller can decide).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from app.services.vector.embedding_service import compute_skill_overlap
from app.utils.logger import logger

# ── Default weight set ────────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "vector_similarity": 0.55,
    "completion_rate": 0.20,
    "average_rating": 0.15,
    "availability_score": 0.05,
    "distance_score": 0.05,
}

FRAUD_SCORE_THRESHOLD = 0.70
FRAUD_SCORE_CAP = 0.10


# ── Signal normalisers ────────────────────────────────────────────────────────


def _normalise_rating(rating: float, max_rating: float = 5.0) -> float:
    """Map [0, max_rating] → [0, 1]."""
    return max(0.0, min(1.0, rating / max_rating))


def _normalise_completion(rate: float) -> float:
    """completion_rate is already in [0, 1] in the model."""
    return max(0.0, min(1.0, float(rate)))


def _availability_score(is_online: bool, current_status: str) -> float:
    """
    Online + available → 1.0
    Online + busy      → 0.5
    Offline            → 0.0
    """
    if not is_online:
        return 0.0
    if current_status in ("available", "online"):
        return 1.0
    if current_status in ("busy", "on_job"):
        return 0.5
    return 0.3


def _distance_score(
    tech_lat: Optional[float],
    tech_lon: Optional[float],
    job_lat: Optional[float],
    job_lon: Optional[float],
    max_km: float = 50.0,
) -> float:
    """
    Inverse-distance score in [0, 1].
    If either location is None → 0.5 (neutral).
    """
    if None in (tech_lat, tech_lon, job_lat, job_lon):
        return 0.5

    # Haversine (fast approximation)
    R = 6371.0
    dlat = math.radians(tech_lat - job_lat)
    dlon = math.radians(tech_lon - job_lon)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(job_lat))
        * math.cos(math.radians(tech_lat))
        * math.sin(dlon / 2) ** 2
    )
    dist_km = 2 * R * math.asin(math.sqrt(a))

    if dist_km >= max_km:
        return 0.0
    return round(1.0 - dist_km / max_km, 4)


# ── Cancellation / response-time penalty ─────────────────────────────────────


def _response_time_bonus(response_time_minutes: int) -> float:
    """
    Faster response → small positive bonus (added to final score, capped).
        < 15 min  → +0.02
        < 60 min  → +0.01
        >= 60 min →  0.00
    """
    if response_time_minutes <= 0:
        return 0.0
    if response_time_minutes < 15:
        return 0.02
    if response_time_minutes < 60:
        return 0.01
    return 0.0


# ── Main ranking function ─────────────────────────────────────────────────────


def rank_candidates(
    candidates: List[Dict[str, Any]],
    job_skills: List[str],
    job_lat: Optional[float] = None,
    job_lon: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
    top_k: int = 100,
) -> List[Dict[str, Any]]:
    """
    Apply hybrid ranking to an ANN candidate list.

    Each candidate dict is expected to have the keys returned by
    `vector_search_service.find_similar_technicians`.

    Returns the list sorted by final_score DESC, enriched with:
        final_score, matched_skills, missing_skills
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    # Normalise weights just in case caller passes non-sum-1
    total = sum(w.values())
    if abs(total - 1.0) > 1e-4:
        logger.warning(f"Ranking weights sum to {total:.3f}, normalising.")
        w = {k: v / total for k, v in w.items()}

    ranked = []
    for cand in candidates:
        sim = float(cand.get("similarity_score", 0.0))
        rating = float(cand.get("average_rating", 0.0))
        comp = float(cand.get("completion_rate", 0.0))
        is_online = bool(cand.get("is_online", False))
        status = cand.get("current_status", "offline")
        t_lat = cand.get("latitude")
        t_lon = cand.get("longitude")
        response_t = int(cand.get("response_time_minutes", 60))
        fraud = float(cand.get("fraud_risk_score", 0.0))
        tech_skills: List[str] = cand.get("skills", [])

        # Compute signals
        avail = _availability_score(is_online, status)
        dist = _distance_score(t_lat, t_lon, job_lat, job_lon)
        norm_rating = _normalise_rating(rating)
        norm_comp = _normalise_completion(comp)
        resp_bonus = _response_time_bonus(response_t)

        # Weighted final score
        final = (
            w["vector_similarity"] * sim
            + w["completion_rate"] * norm_comp
            + w["average_rating"] * norm_rating
            + w["availability_score"] * avail
            + w["distance_score"] * dist
            + resp_bonus
        )
        final = round(min(1.0, max(0.0, final)), 6)

        # Fraud penalty — cap score but keep candidate in list
        if fraud >= FRAUD_SCORE_THRESHOLD:
            final = min(final, FRAUD_SCORE_CAP)

        # Skill overlap analysis
        overlap = compute_skill_overlap(job_skills, tech_skills)

        ranked.append(
            {
                **cand,
                "final_score": final,
                "matched_skills": overlap["matched_skills"],
                "missing_skills": overlap["missing_skills"],
                # breakdown for explainability
                "_score_breakdown": {
                    "vector_similarity": round(sim, 4),
                    "completion_rate": round(norm_comp, 4),
                    "average_rating": round(norm_rating, 4),
                    "availability_score": round(avail, 4),
                    "distance_score": round(dist, 4),
                    "response_bonus": round(resp_bonus, 4),
                    "fraud_penalty_applied": fraud >= FRAUD_SCORE_THRESHOLD,
                },
            }
        )

    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked[:top_k]
