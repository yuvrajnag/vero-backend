from pydantic import BaseModel
from typing import Optional
import uuid

class NegotiationCreate(BaseModel):
    job_request_id: uuid.UUID
    customer_id: uuid.UUID
    technician_id: uuid.UUID
    initial_price: float
    offered_price: float
    ai_recommended_price: Optional[float] = None

class NegotiationUpdate(BaseModel):
    counter_offer: Optional[float] = None
    final_price: Optional[float] = None
    negotiation_status: Optional[str] = None  # pending|accepted|rejected|countered
    accepted_by: Optional[str] = None         # "customer"|"technician"

class NegotiationResponse(BaseModel):
    id: uuid.UUID
    job_request_id: uuid.UUID
    customer_id: uuid.UUID
    technician_id: uuid.UUID
    initial_price: Optional[float]
    offered_price: Optional[float]
    counter_offer: Optional[float]
    final_price: Optional[float]
    ai_recommended_price: Optional[float]
    negotiation_status: str
    accepted_by: Optional[str]

    class Config:
        from_attributes = True
