from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from typing import Optional, List, TYPE_CHECKING, Any
from datetime import datetime, timezone
import uuid
from pgvector.sqlalchemy import Vector

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.assignment import Assignment
    from app.models.technician_portfolio import TechnicianPortfolioEntry


class TechnicianBase(SQLModel):
    # Stage 1 — Basic Information (WorkerOnboarding)
    full_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=15)
    location: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None)
    profile_picture_url: Optional[str] = Field(default=None)

    # Stage 2 — Professional Profile
    role: Optional[str] = Field(default=None, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=255)
    skills: List[str] = Field(default=[], sa_column=Column(JSON))
    experience_years: int = Field(default=0)
    preferred_work_types: List[str] = Field(default=[], sa_column=Column(JSON))
    languages: List[str] = Field(default=[], sa_column=Column(JSON))

    # Stage 3 — Work Preferences
    available_days: List[str] = Field(default=[], sa_column=Column(JSON))
    hours_start: Optional[str] = Field(default=None, max_length=8)  # HH:MM
    hours_end: Optional[str] = Field(default=None, max_length=8)
    remote_pref: Optional[str] = Field(default=None, max_length=50)
    currency: Optional[str] = Field(default=None, max_length=20)
    daily_rate: Optional[float] = Field(default=None)
    preferred_locations: Optional[str] = Field(default=None, max_length=255)
    emergency_availability: Optional[str] = Field(default=None, max_length=10)  # Yes | No | Maybe

    # Stage 4 — Experience & Background
    education: Optional[str] = Field(default=None)
    previous_employers: Optional[str] = Field(default=None)
    work_history: Optional[str] = Field(default=None)
    bio: Optional[str] = Field(default=None)
    resume_url: Optional[str] = Field(default=None)
    linkedin_url: Optional[str] = Field(default=None)

    # Stage 5 — Verification & Proof
    certificates_url: Optional[str] = Field(default=None)
    licenses_url: Optional[str] = Field(default=None)
    government_id_url: Optional[str] = Field(default=None)
    verification_links: List[dict[str, Any]] = Field(
        default=[], sa_column=Column(JSON)
    )  # [{ "platform": "...", "url": "..." }]

    # Worker dashboard — availability custom message
    custom_status_message: Optional[str] = Field(default=None, max_length=72)

    # AI / matching
    skill_embedding: Optional[List[float]] = Field(default=None, sa_column=Column(Vector(384)))
    embedding_updated_at: Optional[datetime] = Field(default=None)
    embedding_version: int = Field(default=0)
    success_score: float = Field(default=0.0)
    fraud_risk_score: float = Field(default=0.0)
    completion_rate: float = Field(default=0.0)
    response_time_minutes: int = Field(default=0)

    # Availability
    is_online: bool = Field(default=True)
    is_emergency_available: bool = Field(default=False)
    current_status: str = Field(default="online", max_length=50)
    last_seen_at: Optional[datetime] = Field(default=None)

    # Pricing (legacy hourly + frontend daily rate)
    base_hourly_rate: Optional[float] = Field(default=None)
    minimum_acceptance_rate: Optional[float] = Field(default=None)
    price: Optional[float] = Field(default=None)
    surge_multiplier: float = Field(default=1.0)

    # Ratings & reputation
    total_jobs_completed: int = Field(default=0)
    total_reviews: int = Field(default=0)
    average_rating: float = Field(default=0.0)

    # Verification
    is_background_verified: bool = Field(default=False)
    verification_level: str = Field(default="basic", max_length=50)

    # Geo
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    service_radius_km: int = Field(default=10)


class Technician(TechnicianBase, table=True):
    __tablename__ = "technician_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="profiles.id", unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional["User"] = Relationship(back_populates="technician_profile")
    assignments: List["Assignment"] = Relationship(back_populates="technician")
    portfolio_entries: List["TechnicianPortfolioEntry"] = Relationship(
        back_populates="technician"
    )
