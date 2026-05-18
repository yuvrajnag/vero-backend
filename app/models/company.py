from sqlmodel import SQLModel, Field, JSON, Column, Relationship
from typing import Optional, List, TYPE_CHECKING, Any
from datetime import datetime, timezone
import uuid

if TYPE_CHECKING:
    from app.models.user import User


class CompanyBase(SQLModel):
    # Stage 1 — Company Information (CompanyOnboarding)
    company_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=15)
    address: Optional[str] = Field(default=None)
    hq_location: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = Field(default=None)

    # Stage 2 — Organization Profile
    industry: Optional[str] = Field(default=None, max_length=100)
    other_industry: Optional[str] = Field(default=None, max_length=255)
    company_size: Optional[str] = Field(default=None, max_length=20)
    business_categories: List[str] = Field(default=[], sa_column=Column(JSON))
    website_url: Optional[str] = Field(default=None, max_length=500)
    operating_regions: List[str] = Field(default=[], sa_column=Column(JSON))
    about: Optional[str] = Field(default=None)

    # Stage 3 — Workforce Preferences
    preferred_workforce_types: List[str] = Field(default=[], sa_column=Column(JSON))
    hiring_frequency: Optional[str] = Field(default=None, max_length=50)
    remote_pref: Optional[str] = Field(default=None, max_length=50)
    urgency_handling: Optional[str] = Field(default=None, max_length=50)
    verification_requirements: List[str] = Field(default=[], sa_column=Column(JSON))
    currency: Optional[str] = Field(default=None, max_length=20)
    project_budget: Optional[float] = Field(default=None)

    # Stage 4 — Operations & Management
    current_team_size: Optional[int] = Field(default=None)
    active_projects_count: Optional[int] = Field(default=None)
    workforce_goals: List[str] = Field(default=[], sa_column=Column(JSON))
    assignment_workflow: Optional[str] = Field(default=None, max_length=50)
    communication_preferences: List[str] = Field(default=[], sa_column=Column(JSON))
    notification_settings: Optional[str] = Field(default=None, max_length=50)

    # Stage 5 — Verification & Security
    registration_doc_url: Optional[str] = Field(default=None)
    tax_docs_url: Optional[str] = Field(default=None)
    identity_verification_url: Optional[str] = Field(default=None)
    portfolio_url: Optional[str] = Field(default=None)
    authorized_rep_name: Optional[str] = Field(default=None, max_length=255)
    verification_links: List[dict[str, Any]] = Field(
        default=[], sa_column=Column(JSON)
    )  # [{ "platform": "...", "url": "..." }]

    # Company dashboard profile edit
    hiring_preferences: Optional[str] = Field(default=None)


class Company(CompanyBase, table=True):
    __tablename__ = "company_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="profiles.id", unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional["User"] = Relationship(back_populates="company_profile")
