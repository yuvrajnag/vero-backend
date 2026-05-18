from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.database import get_session
from app.core.dependencies import get_current_user, get_current_admin, get_current_technician
from app.models.user import User, UserRole, normalize_role
from app.services import job_service
from app.schemas.payment_schema import PaymentCreate, PaymentResponse, WalletResponse
from app.services import payment_service
import uuid

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentResponse)
def process_payment(
    payment_in: PaymentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Initiate a payment for a completed job (customer must own the job)."""
    role = normalize_role(current_user.role)
    if role not in (UserRole.CUSTOMER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only customers can initiate payments")
    if role == UserRole.CUSTOMER and payment_in.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot pay on behalf of another customer")

    payment = payment_service.create_payment(session, payment_in)
    return PaymentResponse.from_payment(payment)


@router.post("/{payment_id}/confirm", response_model=PaymentResponse)
def confirm_payment(
    payment_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Admin: confirm and finalize a payment, releasing funds to technician wallet."""
    payment = payment_service.confirm_payment(session, payment_id)
    return PaymentResponse.from_payment(payment)


@router.get("/wallet/{technician_id}", response_model=WalletResponse)
def get_wallet(
    technician_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get technician wallet balance (own wallet or admin)."""
    role = normalize_role(current_user.role)
    if role == UserRole.TECHNICIAN:
        tech = job_service.get_technician_profile(session, current_user.id)
        if not tech or tech.id != technician_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this wallet")
    elif role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to view wallets")

    wallet = payment_service.get_wallet(session, technician_id)
    return WalletResponse(
        id=wallet.technician_id,
        technician_id=wallet.technician_id,
        balance=wallet.available_balance,
        total_earnings=wallet.total_earned,
        pending_payouts=wallet.pending_balance,
        currency="USD",
    )
