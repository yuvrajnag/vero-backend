from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
import uuid

if TYPE_CHECKING:
    from app.models.technician import Technician


class TechnicianPortfolioEntryBase(SQLModel):
    """Profile page — Add Completed Assignment modal."""

    operation_title: str = Field(max_length=255)
    scope_of_work: Optional[str] = Field(default=None)
    technical_role: Optional[str] = Field(default=None, max_length=255)
    commercial_client: Optional[str] = Field(default=None, max_length=255)
    completion_year: Optional[str] = Field(default=None, max_length=10)
    skills_certifications_applied: List[str] = Field(default=[], sa_column=Column(JSON))
    proof_image_url: Optional[str] = Field(default=None, max_length=500)
    registry_verification_url: Optional[str] = Field(default=None, max_length=500)
    is_featured: bool = Field(default=False)


class TechnicianPortfolioEntry(TechnicianPortfolioEntryBase, table=True):
    __tablename__ = "technician_portfolio_entries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    technician_id: uuid.UUID = Field(foreign_key="technician_profiles.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    technician: Optional["Technician"] = Relationship(back_populates="portfolio_entries")
