from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
import uuid
from enum import Enum
from pgvector.sqlalchemy import Vector

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.assignment import Assignment
    from app.models.technician import Technician


class JobStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class JobBase(SQLModel):
    # Company dashboard — Create Workforce Request
    required_role: Optional[str] = Field(default=None, max_length=255)
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    required_skills: List[str] = Field(default=[], sa_column=Column(JSON))
    budget: Optional[float] = Field(default=None)
    location: Optional[str] = Field(default=None, max_length=255)
    urgency_level: str = Field(default="normal", max_length=20)
    duration: Optional[str] = Field(default=None, max_length=100)
    certifications_required: Optional[str] = Field(default=None)

    proposed_price: Optional[float] = Field(default=None)
    final_price: Optional[float] = Field(default=None)
    price: Optional[float] = Field(default=None)
    status: JobStatus = Field(default=JobStatus.PENDING)

    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    address: Optional[str] = Field(default=None)

    scheduled_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    negotiation_status: str = Field(default="none", max_length=50)
    ai_match_score: Optional[float] = Field(default=None)
    job_embedding: Optional[List[float]] = Field(default=None, sa_column=Column(Vector(384)))


class Job(JobBase, table=True):
    __tablename__ = "job_requests"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    customer_id: Optional[uuid.UUID] = Field(foreign_key="profiles.id", default=None)
    assigned_technician_id: Optional[uuid.UUID] = Field(
        foreign_key="technician_profiles.id", default=None
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    customer: Optional["User"] = Relationship(back_populates="jobs_created")
    assigned_technician: Optional["Technician"] = Relationship()
    assignments: List["Assignment"] = Relationship(back_populates="job")
