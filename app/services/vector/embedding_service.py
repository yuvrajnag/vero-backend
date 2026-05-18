"""
Embedding Service
-----------------
Owns the SentenceTransformer singleton and all logic that converts
structured data (technician profile, job) into 384-dimensional vectors.

Design notes:
- Model is loaded ONCE at module import time (thread-safe for .encode()).
- Helper functions return plain Python lists so they can be stored in
  SQLModel VECTOR columns or serialised to Redis without extra conversion.
- `build_technician_profile_text` and `build_job_profile_text` are kept
  deterministic — same input → same text → same embedding.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.utils.logger import logger

# ── Model singleton ───────────────────────────────────────────────────────────

_model = None
_model_lock = threading.Lock()


def get_model():
    """Return the loaded SentenceTransformer, loading it on first call."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # double-checked locking
                try:
                    from sentence_transformers import SentenceTransformer  # type: ignore
                    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
                    _model = SentenceTransformer(settings.EMBEDDING_MODEL)
                    logger.info("Embedding model loaded successfully.")
                except Exception as exc:
                    logger.error(f"Failed to load embedding model: {exc}")
                    raise RuntimeError(f"Embedding model unavailable: {exc}") from exc
    return _model


# ── Text builders ─────────────────────────────────────────────────────────────


def build_technician_profile_text(tech: Dict[str, Any]) -> str:
    """
    Convert a technician dict (or Technician model_dump()) into a rich
    semantic profile sentence for embedding.

    Fields used (all optional — graceful fallback if missing):
        role, industry, experience_years, skills, bio, education,
        languages, work_history, preferred_work_types, verification_level
    """
    parts: List[str] = []

    role = tech.get("role") or "Technician"
    industry = tech.get("industry") or ""
    exp = tech.get("experience_years") or 0
    skills: List[str] = tech.get("skills") or []
    bio: str = tech.get("bio") or ""
    education: str = tech.get("education") or ""
    languages: List[str] = tech.get("languages") or []
    work_history: str = tech.get("work_history") or ""
    pref_work: List[str] = tech.get("preferred_work_types") or []
    verification: str = tech.get("verification_level") or "basic"
    avg_rating: float = float(tech.get("average_rating") or 0.0)
    completed: int = int(tech.get("total_jobs_completed") or 0)

    # Core identity
    if industry:
        parts.append(f"{role} specialising in {industry} with {exp} years of experience.")
    else:
        parts.append(f"{role} with {exp} years of professional experience.")

    # Skills
    if skills:
        parts.append(f"Core skills: {', '.join(skills)}.")

    # Bio
    if bio:
        parts.append(bio.strip())

    # Work history
    if work_history:
        parts.append(f"Work history: {work_history.strip()}")

    # Education
    if education:
        parts.append(f"Education: {education.strip()}")

    # Languages
    if languages:
        parts.append(f"Languages: {', '.join(languages)}.")

    # Preferred work types
    if pref_work:
        parts.append(f"Preferred work: {', '.join(pref_work)}.")

    # Reputation signals
    if completed > 0:
        parts.append(
            f"Completed {completed} jobs with an average rating of {avg_rating:.1f}/5."
        )

    if verification != "basic":
        parts.append(f"Verification level: {verification}.")

    return " ".join(parts)


def build_job_profile_text(job: Dict[str, Any]) -> str:
    """
    Convert a job dict (or Job model_dump()) into a semantic profile
    sentence for embedding.

    Fields used:
        title, description, required_skills, urgency_level
    """
    parts: List[str] = []

    title: str = job.get("title") or "Untitled Job"
    description: str = job.get("description") or ""
    skills: List[str] = job.get("required_skills") or []
    urgency: str = job.get("urgency_level") or "normal"

    parts.append(f"Job: {title}.")

    if description:
        parts.append(description.strip())

    if skills:
        parts.append(f"Required skills: {', '.join(skills)}.")

    if urgency != "normal":
        parts.append(f"Urgency level: {urgency}.")

    return " ".join(parts)


# ── Core encode functions ─────────────────────────────────────────────────────


def encode_text(text: str) -> List[float]:
    """
    Encode a single text string into a 384-dimensional float list.
    Raises RuntimeError if the model is unavailable.
    """
    if not text or not text.strip():
        return [0.0] * 384

    model = get_model()
    t0 = time.perf_counter()
    vector = model.encode(text, normalize_embeddings=True)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"Encoded text in {elapsed_ms:.1f}ms (len={len(text)})")
    return vector.tolist()


def encode_batch(texts: List[str]) -> List[List[float]]:
    """
    Encode a list of texts in one batched forward pass (much faster than
    calling encode_text() in a loop for large batches).
    """
    if not texts:
        return []

    clean = [t.strip() if t else "" for t in texts]
    model = get_model()
    t0 = time.perf_counter()
    vectors = model.encode(clean, normalize_embeddings=True, batch_size=64)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"Batch-encoded {len(texts)} texts in {elapsed_ms:.1f}ms")
    return [v.tolist() for v in vectors]


def generate_technician_embedding(tech: Dict[str, Any]) -> List[float]:
    """Full pipeline: tech dict → profile text → 384-dim embedding."""
    text = build_technician_profile_text(tech)
    return encode_text(text)


def generate_job_embedding(job: Dict[str, Any]) -> List[float]:
    """Full pipeline: job dict → profile text → 384-dim embedding."""
    text = build_job_profile_text(job)
    return encode_text(text)


# ── Skill overlap helpers (used by ranking service) ──────────────────────────


def compute_skill_overlap(
    job_skills: List[str], tech_skills: List[str]
) -> Dict[str, List[str]]:
    """
    Return matched and missing skills (case-insensitive).
    """
    job_set = {s.lower().strip() for s in job_skills if s}
    tech_set = {s.lower().strip() for s in tech_skills if s}
    matched = sorted(job_set & tech_set)
    missing = sorted(job_set - tech_set)
    return {"matched_skills": matched, "missing_skills": missing}
