"""
Negotiation Acceptance Predictor
----------------------------------
Predicts the probability that a technician will accept a given price offer.

Model: LogisticRegression (scikit-learn)
Falls back to heuristic when model absent.

Model file: trained_models/negotiation_model.joblib
"""
from __future__ import annotations
from typing import Dict, Any
from pathlib import Path

MODEL_PATH = Path(__file__).parents[2] / "ml" / "negotiation_model.joblib"

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


def _build_features(tech: Dict[str, Any], offered_price: float) -> list:
    base_rate = float(tech.get("base_hourly_rate") or 30.0)
    min_rate = float(tech.get("minimum_acceptance_rate") or base_rate * 0.8)
    surge = float(tech.get("surge_multiplier") or 1.0)
    effective_min = min_rate * surge
    ratio = offered_price / effective_min if effective_min > 0 else 1.0
    return [
        ratio,
        float(tech.get("average_rating", 3.0)),
        float(tech.get("total_jobs_completed", 0)),
        float(tech.get("completion_rate", 0.5)),
        1.0 if tech.get("is_online") else 0.0,
    ]


def _heuristic_acceptance(tech: Dict[str, Any], offered_price: float) -> float:
    base_rate = float(tech.get("base_hourly_rate") or 30.0)
    min_rate = float(tech.get("minimum_acceptance_rate") or base_rate * 0.8)
    surge = float(tech.get("surge_multiplier") or 1.0)
    effective_min = min_rate * surge

    if offered_price <= 0 or effective_min <= 0:
        return 0.5

    ratio = offered_price / effective_min
    if ratio >= 1.3:
        return 0.95
    elif ratio >= 1.1:
        return 0.80
    elif ratio >= 1.0:
        return 0.65
    elif ratio >= 0.85:
        return 0.35
    else:
        return 0.10


def predict_acceptance_probability(tech: Dict[str, Any], offered_price: float) -> Dict[str, Any]:
    """
    Returns acceptance probability and a human-readable recommendation.
    """
    model = _load_model()
    if model is not None:
        try:
            features = [_build_features(tech, offered_price)]
            prob = float(model.predict_proba(features)[0][1])
        except Exception:
            prob = _heuristic_acceptance(tech, offered_price)
    else:
        prob = _heuristic_acceptance(tech, offered_price)

    if prob >= 0.75:
        recommendation = "High likelihood of acceptance. Good offer."
    elif prob >= 0.50:
        recommendation = "Moderate chance. Consider a slight increase."
    else:
        recommendation = "Low chance. Offer is below technician's expected rate."

    return {
        "acceptance_probability": round(prob, 4),
        "recommendation": recommendation,
    }
