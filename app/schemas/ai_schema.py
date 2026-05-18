from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid

# ── Skill Matching ──────────────────────────────────────────────────

class SkillMatchRequest(BaseModel):
    job_id: uuid.UUID
    top_k: int = 10

class TechnicianMatchResult(BaseModel):
    technician_id: uuid.UUID
    match_score: float
    skills: List[str]
    experience_years: int
    average_rating: float
    is_online: bool

class SkillMatchResponse(BaseModel):
    job_id: uuid.UUID
    matches: List[TechnicianMatchResult]

# ── Success Probability ─────────────────────────────────────────────

class SuccessProbRequest(BaseModel):
    technician_id: uuid.UUID
    job_id: uuid.UUID

class SuccessProbResponse(BaseModel):
    technician_id: uuid.UUID
    job_id: uuid.UUID
    success_probability: float

# ── Fair Price ──────────────────────────────────────────────────────

class PricePredictRequest(BaseModel):
    technician_id: uuid.UUID
    job_id: uuid.UUID

class PricePredictResponse(BaseModel):
    technician_id: uuid.UUID
    job_id: uuid.UUID
    predicted_price: float
    price_low: float
    price_high: float

# ── Negotiation Acceptance ──────────────────────────────────────────

class NegotiationPredictRequest(BaseModel):
    technician_id: uuid.UUID
    offered_price: float

class NegotiationPredictResponse(BaseModel):
    technician_id: uuid.UUID
    offered_price: float
    acceptance_probability: float
    recommendation: str

# ── Sentiment Analysis ──────────────────────────────────────────────

class SentimentRequest(BaseModel):
    review_id: Optional[uuid.UUID] = None
    text: str

class SentimentResponse(BaseModel):
    sentiment_score: float
    label: str
    is_toxic: bool

# ── Fraud Risk ──────────────────────────────────────────────────────

class FraudScanRequest(BaseModel):
    technician_id: uuid.UUID

class FraudScanResponse(BaseModel):
    technician_id: uuid.UUID
    risk_score: float
    risk_level: str
    reason: str
