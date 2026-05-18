"""
Success Probability Predictor
------------------------------
Predicts the probability that a technician will successfully complete a job.

Model: RandomForestClassifier (scikit-learn) trained on synthetic data.
Falls back to heuristic scoring when model file is absent.

Model file: trained_models/success_model.joblib
"""
from __future__ import annotations
import os
import math
from typing import Optional, Dict, Any
from pathlib import Path

MODEL_PATH = Path(__file__).parents[2] / "ml" / "success_model.joblib"

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib
        _model = joblib.load(MODEL_PATH)
        return _model
    except Exception:
        return None


def _build_features(tech: Dict[str, Any], job: Dict[str, Any]) -> list:
    return [
        float(tech.get("experience_years", 0)),
        float(tech.get("completion_rate", 0.0)),
        float(tech.get("average_rating", 0.0)),
        float(tech.get("total_jobs_completed", 0)),
        float(tech.get("response_time_minutes", 60)),
        float(tech.get("fraud_risk_score", 0.0)),
        1.0 if tech.get("is_background_verified") else 0.0,
        float(job.get("budget", 0)),
        1.0 if job.get("urgency_level") == "emergency" else 0.0,
    ]


def _heuristic_score(tech: Dict[str, Any], job: Dict[str, Any]) -> float:
    """Rule-based fallback when model isn't trained yet."""
    score = 0.5
    score += min(tech.get("experience_years", 0) * 0.02, 0.15)
    score += tech.get("completion_rate", 0.0) * 0.20
    score += (tech.get("average_rating", 0.0) / 5.0) * 0.15
    score -= tech.get("fraud_risk_score", 0.0) * 0.20
    score += 0.05 if tech.get("is_background_verified") else 0.0
    # Penalise slow response
    resp = tech.get("response_time_minutes", 60)
    if resp < 15:
        score += 0.05
    elif resp > 120:
        score -= 0.05
    return round(max(0.0, min(1.0, score)), 4)


def predict_success_probability(tech: Dict[str, Any], job: Dict[str, Any]) -> float:
    """
    Returns a float in [0, 1] representing job completion probability.

    Parameters
    ----------
    tech : dict with keys matching Technician model fields
    job  : dict with keys matching Job model fields
    """
    model = _load_model()
    if model is not None:
        try:
            features = [_build_features(tech, job)]
            prob = model.predict_proba(features)[0][1]
            return round(float(prob), 4)
        except Exception:
            pass
    return _heuristic_score(tech, job)
