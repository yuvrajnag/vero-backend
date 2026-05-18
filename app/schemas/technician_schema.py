from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
import uuid
from datetime import datetime

from app.schemas.common_schema import VerificationLink


class TechnicianOnboardingFields(BaseModel):
    """Fields collected in WorkerOnboarding (all optional on update)."""

    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=15)
    location: Optional[str] = None
    address: Optional[str] = None
    profile_picture_url: Optional[str] = None

    role: Optional[str] = None
    industry: Optional[str] = None
    skills: List[str] = []
    experience_years: int = 0
    preferred_work_types: List[str] = []
    languages: List[str] = []

    available_days: List[str] = []
    hours_start: Optional[str] = Field(default=None, max_length=8)
    hours_end: Optional[str] = Field(default=None, max_length=8)
    remote_pref: Optional[str] = None
    currency: Optional[str] = None
    daily_rate: Optional[float] = None
    base_hourly_rate: Optional[float] = None  # legacy / frontend alias → daily_rate
    price: Optional[float] = None
    preferred_locations: Optional[str] = None
    emergency_availability: Optional[str] = Field(default=None, max_length=10)

    education: Optional[str] = None
    previous_employers: Optional[str] = None
    work_history: Optional[str] = None
    bio: Optional[str] = None
    resume_url: Optional[str] = None
    linkedin_url: Optional[str] = None

    certificates_url: Optional[str] = None
    licenses_url: Optional[str] = None
    government_id_url: Optional[str] = None
    verification_links: List[VerificationLink] = []

    custom_status_message: Optional[str] = Field(default=None, max_length=72)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @model_validator(mode="after")
    def map_rate_fields(self) -> "TechnicianOnboardingFields":
        if self.daily_rate is None and self.base_hourly_rate is not None:
            self.daily_rate = self.base_hourly_rate
        return self

    def technician_columns(self) -> dict:
        data = self.model_dump(exclude={"base_hourly_rate"}, exclude_none=True)
        links = data.get("verification_links")
        if links is not None:
            data["verification_links"] = [
                item if isinstance(item, dict) else item.model_dump()
                for item in links
            ]
        return data


class TechnicianCreate(TechnicianOnboardingFields):
    skills: List[str] = Field(min_length=1)
    experience_years: int = Field(ge=0)


class TechnicianUpdate(TechnicianOnboardingFields):
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = Field(default=None, ge=0)
    is_online: Optional[bool] = None
    current_status: Optional[str] = None


class TechnicianResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    profile_picture_url: Optional[str] = None
    role: Optional[str] = None
    industry: Optional[str] = None
    skills: List[str] = []
    experience_years: int = 0
    preferred_work_types: List[str] = []
    languages: List[str] = []
    available_days: List[str] = []
    hours_start: Optional[str] = None
    hours_end: Optional[str] = None
    remote_pref: Optional[str] = None
    currency: Optional[str] = None
    daily_rate: Optional[float] = None
    preferred_locations: Optional[str] = None
    emergency_availability: Optional[str] = None
    education: Optional[str] = None
    previous_employers: Optional[str] = None
    work_history: Optional[str] = None
    bio: Optional[str] = None
    resume_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    certificates_url: Optional[str] = None
    licenses_url: Optional[str] = None
    government_id_url: Optional[str] = None
    verification_links: List[dict] = []
    custom_status_message: Optional[str] = None
    is_online: bool = False
    current_status: str = "offline"
    base_hourly_rate: Optional[float] = None
    price: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    average_rating: float = 0.0
    success_score: float = 0.0
    fraud_risk_score: float = 0.0
    total_jobs_completed: int = 0
    verification_level: str = "basic"
    created_at: datetime
    updated_at: datetime

    @field_validator("verification_links", mode="before")
    @classmethod
    def normalize_links(cls, v):
        if v is None:
            return []
        return v

    class Config:
        from_attributes = True
