"""
Fraud Risk Detector
--------------------
Detects anomalous technician behaviour using Isolation Forest.
Falls back to rule-based scoring when model absent.

Features used:
  - trust_score, completion_rate, average_rating
  - total_jobs_completed, response_time_minutes
  - fraud_risk_score (historical)

Model file: trained_models/fraud_model.joblib
Score returned: float in [0, 1] where 1 = highest risk.
"""
from __future__ import annotations
from typing import Dict, Any
from pathlib import Path

MODEL_PATH = Path(__file__).parents[2] / "ml" / "fraud_model.joblib"

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


def _build_features(tech: Dict[str, Any]) -> list:
    return [
        float(tech.get("trust_score", 0.0)),
        float(tech.get("completion_rate", 0.0)),
        float(tech.get("average_rating", 0.0)),
        float(tech.get("total_jobs_completed", 0)),
        float(tech.get("response_time_minutes", 60)),
        float(tech.get("fraud_risk_score", 0.0)),
        1.0 if tech.get("is_background_verified") else 0.0,
    ]


def _heuristic_risk(tech: Dict[str, Any]) -> float:
    """
    Rule-based risk score. High risk = close to 1.
    """
    risk = 0.0

    # Low trust score
    trust = tech.get("trust_score", 0.0)
    risk += (1.0 - min(trust / 100.0, 1.0)) * 0.25

    # Low completion rate
    cr = tech.get("completion_rate", 0.0)
    risk += (1.0 - cr) * 0.20

    # Poor rating
    rating = tech.get("average_rating", 5.0)
    risk += max(0.0, (3.0 - rating) / 3.0) * 0.20

    # Existing fraud history
    hist = tech.get("fraud_risk_score", 0.0)
    risk += hist * 0.25

    # Not verified
    if not tech.get("is_background_verified"):
        risk += 0.10

    return round(min(risk, 1.0), 4)


def compute_fraud_risk(tech: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns:
        risk_score : float in [0, 1]
        risk_level : "low" | "medium" | "high"
        reason     : human-readable explanation
    """
    model = _load_model()
    if model is not None:
        try:
            features = [_build_features(tech)]
            # IsolationForest: -1 = anomaly, 1 = normal
            prediction = model.predict(features)[0]
            raw_score = model.decision_function(features)[0]
            # Normalize: more negative = more anomalous = higher risk
            risk_score = round(max(0.0, min(1.0, 0.5 - raw_score * 0.5)), 4)
        except Exception:
            risk_score = _heuristic_risk(tech)
    else:
        risk_score = _heuristic_risk(tech)

    if risk_score >= 0.70:
        level, reason = "high", "Multiple anomalous signals detected. Manual review recommended."
    elif risk_score >= 0.40:
        level, reason = "medium", "Some unusual patterns. Monitor closely."
    else:
        level, reason = "low", "No significant risk indicators."

    return {"risk_score": risk_score, "risk_level": level, "reason": reason}
