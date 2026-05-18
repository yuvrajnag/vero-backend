from typing import List, Dict

SUCCESS_FEATURES = [
    "experience_years", "completion_rate", "average_rating", 
    "total_jobs_completed", "response_time_minutes", "fraud_risk_score", 
    "is_background_verified", "budget", "urgency_is_emergency"
]

PRICE_FEATURES = [
    "experience_years", "average_rating", "base_hourly_rate", 
    "num_skills", "budget", "urgency_score", "is_background_verified"
]

NEGOTIATION_FEATURES = [
    "offer_ratio", "average_rating", "total_jobs_completed", 
    "completion_rate", "is_online"
]

FRAUD_FEATURES = [
    "trust_score", "completion_rate", "average_rating", 
    "total_jobs_completed", "response_time_minutes", "fraud_risk_score", 
    "is_background_verified"
]

FEATURE_DESCRIPTIONS = {
    "experience_years": "technician experience level",
    "completion_rate": "historical completion rate",
    "average_rating": "customer ratings",
    "total_jobs_completed": "total jobs completed",
    "response_time_minutes": "response time",
    "fraud_risk_score": "fraud risk history",
    "is_background_verified": "background verification status",
    "budget": "job budget",
    "urgency_is_emergency": "emergency urgency level",
    "base_hourly_rate": "base hourly rate",
    "num_skills": "number of matching skills",
    "urgency_score": "job urgency score",
    "offer_ratio": "offered price relative to expected minimum",
    "is_online": "current online status",
    "trust_score": "system trust score",
}

def get_feature_name(feature_name: str) -> str:
    return FEATURE_DESCRIPTIONS.get(feature_name, feature_name.replace("_", " "))
