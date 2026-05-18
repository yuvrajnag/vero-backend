from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
import uuid

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.technician import Technician
    from app.models.user import User

class TechnicianWalletBase(SQLModel):
    total_earned: float = Field(default=0.0)
    available_balance: float = Field(default=0.0)
    pending_balance: float = Field(default=0.0)
    lifetime_jobs: int = Field(default=0)

class TechnicianWallet(TechnicianWalletBase, table=True):
    __tablename__ = "technician_wallets"
    technician_id: uuid.UUID = Field(foreign_key="technician_profiles.id", primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # technician: Optional["Technician"] = Relationship()

class PaymentBase(SQLModel):
    amount: float
    platform_fee: float = Field(default=0.0)
    technician_payout: float = Field(default=0.0)
    payment_status: str = Field(default="pending")
    payment_method: Optional[str] = Field(default=None)
    transaction_reference: Optional[str] = Field(default=None)
    paid_at: Optional[datetime] = Field(default=None)

class Payment(PaymentBase, table=True):
    __tablename__ = "payments"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_request_id: uuid.UUID = Field(foreign_key="job_requests.id")
    customer_id: uuid.UUID = Field(foreign_key="profiles.id")
    technician_id: Optional[uuid.UUID] = Field(foreign_key="technician_profiles.id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
