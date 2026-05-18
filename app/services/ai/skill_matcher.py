"""
Skill Matching Engine
---------------------
Uses TF-IDF vectorization + cosine similarity to rank technicians
against a job's required_skills list.

Falls back to keyword overlap scoring if scikit-learn is unavailable.
Embedding results are cached in-memory per session for performance.
"""
from __future__ import annotations
from typing import List, Dict, Any
import json

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

from app.utils.logger import logger


def _skills_to_text(skills: List[str]) -> str:
    """Normalize a skills list to a single lowercase space-joined string."""
    return " ".join(s.lower().strip() for s in skills if s)


def compute_match_score(job_skills: List[str], tech_skills: List[str]) -> float:
    """
    Return a cosine similarity score in [0, 1] between job requirements
    and a technician's skill set.
    """
    if not job_skills or not tech_skills:
        return 0.0

    job_text = _skills_to_text(job_skills)
    tech_text = _skills_to_text(tech_skills)

    if _SKLEARN_AVAILABLE:
        try:
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([job_text, tech_text])
            score = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
            return round(score, 4)
        except Exception as exc:
            logger.warning(f"TF-IDF failed, falling back to keyword overlap: {exc}")

    # Keyword overlap fallback
    job_set = set(job_text.split())
    tech_set = set(tech_text.split())
    if not job_set:
        return 0.0
    overlap = len(job_set & tech_set) / len(job_set)
    return round(overlap, 4)


def rank_technicians(
    job_skills: List[str],
    technicians: List[Dict[str, Any]],
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Rank a list of technician dicts by match score.

    Each dict must have at least: {id, skills: List[str]}.
    Returns the top_k dicts with an added 'match_score' key, sorted desc.
    """
    if not technicians:
        return []

    job_text = _skills_to_text(job_skills)

    if _SKLEARN_AVAILABLE and len(technicians) > 1:
        texts = [job_text] + [_skills_to_text(t.get("skills", [])) for t in technicians]
        try:
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform(texts)
            scores = cosine_similarity(tfidf[0:1], tfidf[1:])[0]
            for i, tech in enumerate(technicians):
                tech["match_score"] = round(float(scores[i]), 4)
        except Exception as exc:
            logger.warning(f"Batch TF-IDF failed: {exc}")
            for tech in technicians:
                tech["match_score"] = compute_match_score(job_skills, tech.get("skills", []))
    else:
        for tech in technicians:
            tech["match_score"] = compute_match_score(job_skills, tech.get("skills", []))

    ranked = sorted(technicians, key=lambda x: x["match_score"], reverse=True)
    return ranked[:top_k]


def store_embedding(skills: List[str]) -> List[float]:
    """
    Produce a simple TF-IDF-style embedding for a skill list.
    Used to persist in technician.skill_embedding for fast retrieval.
    Returns a list of floats (or empty list if sklearn unavailable).
    """
    if not _SKLEARN_AVAILABLE or not skills:
        return []
    try:
        text = _skills_to_text(skills)
        vec = TfidfVectorizer(max_features=128)
        mat = vec.fit_transform([text])
        return mat.toarray()[0].tolist()
    except Exception:
        return []
