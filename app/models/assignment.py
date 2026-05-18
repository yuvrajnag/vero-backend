from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
import uuid
from enum import Enum

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.technician import Technician

class AssignmentStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class AssignmentBase(SQLModel):
    assignment_status: AssignmentStatus = Field(default=AssignmentStatus.PENDING)
    assigned_by: Optional[uuid.UUID] = Field(default=None)
    assigned_at: Optional[datetime] = Field(default=None)
    accepted_at: Optional[datetime] = Field(default=None)
    rejected_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    cancellation_reason: Optional[str] = Field(default=None)

class Assignment(AssignmentBase, table=True):
    __tablename__ = "job_assignments"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_request_id: uuid.UUID = Field(foreign_key="job_requests.id")
    technician_id: uuid.UUID = Field(foreign_key="technician_profiles.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    job: Optional["Job"] = Relationship(back_populates="assignments")
    technician: Optional["Technician"] = Relationship(back_populates="assignments")
