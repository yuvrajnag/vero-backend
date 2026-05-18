from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class ReviewCreate(BaseModel):
    job_request_id: uuid.UUID
    technician_id: uuid.UUID
    rating: float = Field(ge=0.0, le=5.0)
    review_text: Optional[str] = None

class ReviewResponse(BaseModel):
    id: uuid.UUID
    job_request_id: uuid.UUID
    customer_id: uuid.UUID
    technician_id: uuid.UUID
    rating: float
    review_text: Optional[str]
    sentiment_score: Optional[float]
    is_flagged: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
