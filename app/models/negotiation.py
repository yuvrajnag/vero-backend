from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
import uuid

class NegotiationLogBase(SQLModel):
    initial_price: Optional[float] = Field(default=None)
    offered_price: Optional[float] = Field(default=None)
    counter_offer: Optional[float] = Field(default=None)
    final_price: Optional[float] = Field(default=None)
    negotiation_status: str = Field(default="pending")
    accepted_by: Optional[str] = Field(default=None)
    ai_recommended_price: Optional[float] = Field(default=None)

class NegotiationLog(NegotiationLogBase, table=True):
    __tablename__ = "negotiation_logs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_request_id: uuid.UUID = Field(foreign_key="job_requests.id")
    customer_id: uuid.UUID = Field(foreign_key="profiles.id")
    technician_id: uuid.UUID = Field(foreign_key="technician_profiles.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
