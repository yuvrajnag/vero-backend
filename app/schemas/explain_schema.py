from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import uuid

class ExplanationDetail(BaseModel):
    feature: str
    impact: str
    reason: str

class ExplainSuccessResponse(BaseModel):
    prediction: float
    explanations: List[ExplanationDetail]
    summary_plot: Optional[Dict[str, Any]] = None

class ExplainPriceResponse(BaseModel):
    predicted_price: float
    explanations: List[ExplanationDetail]
    summary_plot: Optional[Dict[str, Any]] = None

class ExplainNegotiationResponse(BaseModel):
    acceptance_probability: float
    explanations: List[ExplanationDetail]
    summary_plot: Optional[Dict[str, Any]] = None

class ExplainFraudResponse(BaseModel):
    risk_score: float
    explanations: List[ExplanationDetail]
    summary_plot: Optional[Dict[str, Any]] = None

class ExplainMatchResponse(BaseModel):
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    explanations: List[str]

class ExplainRequest(BaseModel):
    technician_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    offered_price: Optional[float] = None
