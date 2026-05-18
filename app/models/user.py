from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.technician import Technician
    from app.models.company import Company
    from app.models.job import Job
from datetime import datetime, timezone
import uuid
from enum import Enum

class UserRole(str, Enum):
    """Values must match the Postgres `userrole` enum (uppercase)."""
    ADMIN = "ADMIN"
    TECHNICIAN = "TECHNICIAN"
    CUSTOMER = "CUSTOMER"


def normalize_role(role: str | UserRole | None) -> UserRole:
    if role is None:
        return UserRole.CUSTOMER
    if isinstance(role, UserRole):
        return role
    key = str(role).strip().lower()
    mapping = {
        "admin": UserRole.ADMIN,
        "technician": UserRole.TECHNICIAN,
        "customer": UserRole.CUSTOMER,
    }
    if key not in mapping:
        raise ValueError(f"Invalid role: {role}")
    return mapping[key]


def role_for_api(role: str | UserRole | None) -> str | None:
    if role is None:
        return None
    return str(role).lower()

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=UserRole.CUSTOMER.value, index=True)
    is_active: bool = Field(default=True)
    hashed_password: Optional[str] = Field(default=None)
    user_type: Optional[str] = Field(default=None)
    onboarding_completed: bool = Field(default=False)
    profile_status: str = Field(default="active")
    is_verified: bool = Field(default=False)
    trust_score: float = Field(default=0.0)
    last_active_at: Optional[datetime] = Field(default=None)
    google_id: Optional[str] = Field(default=None, unique=True, index=True)

class User(UserBase, table=True):
    __tablename__ = "profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    technician_profile: Optional["Technician"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    company_profile: Optional["Company"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    jobs_created: List["Job"] = Relationship(back_populates="customer")
