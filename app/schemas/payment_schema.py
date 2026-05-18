from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

from app.models.payment import Payment


class PaymentCreate(BaseModel):
    job_id: uuid.UUID
    customer_id: uuid.UUID
    technician_id: Optional[uuid.UUID] = None
    amount: float
    currency: str = "USD"
    payment_method: Optional[str] = None


class PaymentResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    customer_id: uuid.UUID
    technician_id: Optional[uuid.UUID]
    amount: float
    platform_fee: float
    technician_payout: float
    currency: str = "USD"
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_payment(cls, payment: Payment) -> "PaymentResponse":
        return cls(
            id=payment.id,
            job_id=payment.job_request_id,
            customer_id=payment.customer_id,
            technician_id=payment.technician_id,
            amount=payment.amount,
            platform_fee=payment.platform_fee,
            technician_payout=payment.technician_payout,
            currency="USD",
            status=payment.payment_status,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )


class WalletResponse(BaseModel):
    id: uuid.UUID
    technician_id: uuid.UUID
    balance: float
    total_earnings: float
    pending_payouts: float
    currency: str
