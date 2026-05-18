from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.payment import Payment, TechnicianWallet
from app.schemas.payment_schema import PaymentCreate
import uuid

PLATFORM_FEE_RATE = 0.10  # 10%

def create_payment(session: Session, payment_data: PaymentCreate) -> Payment:
    technician_payout = round(payment_data.amount * (1 - PLATFORM_FEE_RATE), 2)
    platform_fee = round(payment_data.amount * PLATFORM_FEE_RATE, 2)

    payment = Payment(
        job_request_id=payment_data.job_id,
        customer_id=payment_data.customer_id,
        technician_id=payment_data.technician_id,
        amount=payment_data.amount,
        platform_fee=platform_fee,
        technician_payout=technician_payout,
        payment_method=payment_data.payment_method,
        payment_status="pending",
    )
    session.add(payment)

    # Update technician wallet if technician is assigned
    if payment_data.technician_id:
        wallet = session.exec(
            select(TechnicianWallet).where(TechnicianWallet.technician_id == payment_data.technician_id)
        ).first()
        if not wallet:
            wallet = TechnicianWallet(technician_id=payment_data.technician_id)
        wallet.pending_balance += technician_payout
        session.add(wallet)

    session.commit()
    session.refresh(payment)
    return payment

def get_wallet(session: Session, technician_id: uuid.UUID) -> TechnicianWallet:
    wallet = session.exec(
        select(TechnicianWallet).where(TechnicianWallet.technician_id == technician_id)
    ).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet

def confirm_payment(session: Session, payment_id: uuid.UUID) -> Payment:
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.payment_status == "completed":
        raise HTTPException(status_code=400, detail="Payment already completed")

    from datetime import datetime, timezone
    payment.payment_status = "completed"
    payment.paid_at = datetime.now(timezone.utc)

    # Move pending → available in wallet
    if payment.technician_id:
        wallet = session.exec(
            select(TechnicianWallet).where(TechnicianWallet.technician_id == payment.technician_id)
        ).first()
        if wallet:
            wallet.pending_balance = max(0, wallet.pending_balance - payment.technician_payout)
            wallet.available_balance += payment.technician_payout
            wallet.total_earned += payment.technician_payout
            wallet.lifetime_jobs += 1
            session.add(wallet)

    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment
