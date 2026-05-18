from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
import uuid

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.technician import Technician
    from app.models.user import User

class ReviewBase(SQLModel):
    rating: float = Field(ge=0.0, le=5.0)
    review_text: Optional[str] = Field(default=None)
    sentiment_score: Optional[float] = Field(default=None)
    is_flagged: bool = Field(default=False)

class TechnicianReview(ReviewBase, table=True):
    __tablename__ = "technician_reviews"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_request_id: uuid.UUID = Field(foreign_key="job_requests.id", unique=True)
    customer_id: uuid.UUID = Field(foreign_key="profiles.id")
    technician_id: uuid.UUID = Field(foreign_key="technician_profiles.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
