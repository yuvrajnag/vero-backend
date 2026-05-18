from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from app.models.job import JobStatus
import uuid
from datetime import datetime


class JobCreate(BaseModel):
    required_role: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: List[str] = []
    budget: Optional[float] = None
    price: Optional[float] = None
    location: Optional[str] = None
    urgency_level: str = "normal"
    duration: Optional[str] = None
    certifications_required: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    scheduled_at: Optional[datetime] = None

    @model_validator(mode="after")
    def ensure_title(self) -> "JobCreate":
        if not self.title:
            if self.required_role:
                self.title = self.required_role
            else:
                raise ValueError("Either title or required_role is required")
        return self


class JobUpdate(BaseModel):
    required_role: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[JobStatus] = None
    required_skills: Optional[List[str]] = None
    budget: Optional[float] = None
    price: Optional[float] = None
    location: Optional[str] = None
    urgency_level: Optional[str] = None
    duration: Optional[str] = None
    certifications_required: Optional[str] = None


class JobResponse(BaseModel):
    id: uuid.UUID
    customer_id: Optional[uuid.UUID]
    assigned_technician_id: Optional[uuid.UUID] = None
    required_role: Optional[str] = None
    title: str
    description: Optional[str] = None
    required_skills: List[str] = []
    budget: Optional[float] = None
    price: Optional[float] = None
    location: Optional[str] = None
    urgency_level: str
    duration: Optional[str] = None
    certifications_required: Optional[str] = None
    status: JobStatus
    ai_match_score: Optional[float] = None
    negotiation_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
