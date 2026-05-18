from sqlmodel import SQLModel, Field, JSON, Column
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid

class AIRecommendationLogBase(SQLModel):
    ai_match_score: Optional[float] = Field(default=None)
    recommendation_rank: Optional[int] = Field(default=None)
    selected: Optional[bool] = Field(default=None)
    success: Optional[bool] = Field(default=None)

class AIRecommendationLog(AIRecommendationLogBase, table=True):
    __tablename__ = "ai_recommendation_logs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_request_id: Optional[uuid.UUID] = Field(foreign_key="job_requests.id", default=None)
    technician_id: Optional[uuid.UUID] = Field(foreign_key="technician_profiles.id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExplainabilityLog(SQLModel, table=True):
    __tablename__ = "explainability_logs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_name: str = Field(index=True)
    prediction_id: Optional[str] = Field(default=None, index=True)
    explanation_json: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
