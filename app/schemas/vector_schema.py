"""
Vector Search Pydantic Schemas
-------------------------------
All request/response models for the /ai/vector/* endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import uuid


# ── Match Technicians ─────────────────────────────────────────────────────────


class VectorMatchRequest(BaseModel):
    """POST /ai/vector/match-technicians"""

    job_id: uuid.UUID
    top_k: int = Field(default=20, ge=1, le=100)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    weights: Optional[Dict[str, float]] = Field(
        default=None,
        description=(
            "Override ranking weights. Keys: vector_similarity, completion_rate, "
            "average_rating, availability_score, distance_score"
        ),
    )

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v):
        if v is None:
            return v
        allowed = {
            "vector_similarity",
            "completion_rate",
            "average_rating",
            "availability_score",
            "distance_score",
        }
        for k in v:
            if k not in allowed:
                raise ValueError(f"Unknown weight key: {k}")
            if not 0.0 <= v[k] <= 1.0:
                raise ValueError(f"Weight {k} must be in [0, 1]")
        return v


class ScoreBreakdown(BaseModel):
    vector_similarity: float
    completion_rate: float
    average_rating: float
    availability_score: float
    distance_score: float
    response_bonus: float
    fraud_penalty_applied: bool


class VectorMatchResult(BaseModel):
    technician_id: str
    similarity_score: float
    final_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    experience_years: int
    average_rating: float
    completion_rate: float
    is_online: bool
    current_status: str
    total_jobs_completed: int
    base_hourly_rate: Optional[float]
    score_breakdown: Optional[ScoreBreakdown] = None


class VectorMatchResponse(BaseModel):
    job_id: uuid.UUID
    total_candidates: int
    cached: bool
    latency_ms: float
    matches: List[VectorMatchResult]


# ── Semantic Search ───────────────────────────────────────────────────────────


class VectorSearchRequest(BaseModel):
    """POST /ai/vector/search — free-text semantic technician search"""

    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=20, ge=1, le=100)
    min_similarity: float = Field(default=0.1, ge=0.0, le=1.0)
    only_online: bool = False


class VectorSearchResult(BaseModel):
    technician_id: str
    similarity_score: float
    skills: List[str]
    experience_years: int
    average_rating: float
    is_online: bool


class VectorSearchResponse(BaseModel):
    query: str
    total_results: int
    cached: bool
    latency_ms: float
    results: List[VectorSearchResult]


# ── Update Technician Embedding ───────────────────────────────────────────────


class UpdateTechnicianEmbeddingRequest(BaseModel):
    """POST /ai/vector/update-technician"""

    technician_id: uuid.UUID


class UpdateEmbeddingResponse(BaseModel):
    entity_type: str
    entity_id: str
    success: bool
    message: str
    queued: bool = False


# ── Update Job Embedding ──────────────────────────────────────────────────────


class UpdateJobEmbeddingRequest(BaseModel):
    """POST /ai/vector/update-job"""

    job_id: uuid.UUID


# ── Full Rebuild ──────────────────────────────────────────────────────────────


class RebuildRequest(BaseModel):
    """POST /ai/vector/rebuild"""

    target: str = Field(
        default="all",
        description="'technicians' | 'jobs' | 'all'",
    )

    @field_validator("target")
    @classmethod
    def validate_target(cls, v):
        allowed = {"technicians", "jobs", "all"}
        if v not in allowed:
            raise ValueError(f"target must be one of {allowed}")
        return v


class RebuildResponse(BaseModel):
    target: str
    technicians: Optional[Dict[str, int]] = None
    jobs: Optional[Dict[str, int]] = None
    message: str


# ── Analytics ─────────────────────────────────────────────────────────────────


class VectorAnalyticsResponse(BaseModel):
    analytics: Dict[str, Any]
    worker_running: bool
