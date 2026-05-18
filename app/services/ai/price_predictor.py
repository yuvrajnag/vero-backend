"""
Fair Price Predictor
---------------------
Predicts a fair market price for a job given technician and job attributes.

Model: GradientBoostingRegressor (scikit-learn) — lightweight XGBoost equivalent.
Falls back to heuristic when model absent.

Model file: trained_models/price_model.joblib
"""
from __future__ import annotations
from typing import Dict, Any, Tuple
from pathlib import Path

MODEL_PATH = Path(__file__).parents[2] / "ml" / "price_model.joblib"

_model = None

URGENCY_MULTIPLIERS = {"normal": 1.0, "urgent": 1.25, "emergency": 1.60}
BASE_RATE_PER_YEAR_EXP = 5.0   # $5 extra per year of experience
PLATFORM_FLOOR = 20.0


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
    urgency_score = {"normal": 0, "urgent": 1, "emergency": 2}.get(
        job.get("urgency_level", "normal"), 0
    )
    return [
        float(tech.get("experience_years", 0)),
        float(tech.get("average_rating", 0.0)),
        float(tech.get("base_hourly_rate") or 30.0),
        float(len(tech.get("skills", []))),
        float(job.get("budget", 100)),
        float(urgency_score),
        1.0 if tech.get("is_background_verified") else 0.0,
    ]


def _heuristic_price(tech: Dict[str, Any], job: Dict[str, Any]) -> float:
    base = float(tech.get("base_hourly_rate") or 30.0)
    base += tech.get("experience_years", 0) * BASE_RATE_PER_YEAR_EXP
    multiplier = URGENCY_MULTIPLIERS.get(job.get("urgency_level", "normal"), 1.0)
    rating = tech.get("average_rating", 3.0)
    rating_bonus = (rating - 3.0) * 5.0  # ±$5 per rating point above/below 3
    price = (base + rating_bonus) * multiplier
    return round(max(PLATFORM_FLOOR, price), 2)


def predict_fair_price(tech: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, float]:
    """
    Returns a dict with:
        predicted_price  : point estimate
        price_low        : lower bound (−15%)
        price_high       : upper bound (+15%)
    """
    model = _load_model()
    if model is not None:
        try:
            features = [_build_features(tech, job)]
            price = float(model.predict(features)[0])
        except Exception:
            price = _heuristic_price(tech, job)
    else:
        price = _heuristic_price(tech, job)

    return {
        "predicted_price": round(price, 2),
        "price_low": round(price * 0.85, 2),
        "price_high": round(price * 1.15, 2),
    }
