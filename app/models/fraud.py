from sqlmodel import SQLModel, Field, JSON, Column
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class FraudDetectionLogBase(SQLModel):
    risk_score: float = Field(default=0.0)
    fraud_reason: str
    action_taken: Optional[str] = Field(default=None)
    reviewed_by: Optional[uuid.UUID] = Field(default=None)

class FraudDetectionLog(FraudDetectionLogBase, table=True):
    __tablename__ = "fraud_detection_logs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    technician_id: Optional[uuid.UUID] = Field(foreign_key="technician_profiles.id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = Field(default=None)
