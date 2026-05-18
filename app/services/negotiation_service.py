from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.negotiation import NegotiationLog
from app.models.job import Job, JobStatus
from app.models.technician import Technician
from app.schemas.negotiation_schema import NegotiationCreate, NegotiationUpdate
from app.schemas.dashboard_schema import NegotiationDashboardItem
from app.schemas.notification_schema import NotificationCreate
from app.services import job_service, notification_service
from typing import List
import uuid

def create_negotiation(session: Session, negotiation_in: NegotiationCreate) -> NegotiationLog:
    # Only one active negotiation per job
    existing = session.exec(
        select(NegotiationLog)
        .where(NegotiationLog.job_request_id == negotiation_in.job_request_id)
        .where(NegotiationLog.negotiation_status == "pending")
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Active negotiation already exists for this job")

    log = NegotiationLog(
        job_request_id=negotiation_in.job_request_id,
        customer_id=negotiation_in.customer_id,
        technician_id=negotiation_in.technician_id,
        initial_price=negotiation_in.initial_price,
        offered_price=negotiation_in.offered_price,
        ai_recommended_price=negotiation_in.ai_recommended_price,
    )
    session.add(log)

    # Update job status
    job = session.get(Job, negotiation_in.job_request_id)
    if job:
        job.status = JobStatus.NEGOTIATING
        job.negotiation_status = "pending"
        session.add(job)

    session.commit()
    session.refresh(log)

    tech = session.get(Technician, negotiation_in.technician_id)
    if tech:
        notification_service.send_notification(
            session,
            NotificationCreate(
                user_id=tech.user_id,
                title="New negotiation offer",
                message="A company started a rate negotiation on one of your matched jobs.",
                notification_type="negotiation",
                action_url="/dashboard/worker",
            ),
        )
    return log


def update_negotiation(session: Session, negotiation_id: uuid.UUID, update_in: NegotiationUpdate) -> NegotiationLog:
    log = session.get(NegotiationLog, negotiation_id)
    if not log:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    if update_in.counter_offer is not None:
        log.counter_offer = update_in.counter_offer
    if update_in.negotiation_status:
        log.negotiation_status = update_in.negotiation_status
    if update_in.final_price is not None:
        log.final_price = update_in.final_price
    if update_in.accepted_by:
        log.accepted_by = update_in.accepted_by

    if update_in.negotiation_status == "accepted":
        final = log.final_price or log.counter_offer or log.offered_price
        log.final_price = final
        job = session.get(Job, log.job_request_id)
        if job:
            job.status = JobStatus.ACCEPTED
            job.final_price = final
            job.negotiation_status = "accepted"
            session.add(job)
        job_service.assign_technician(session, log.job_request_id, log.technician_id)
        notification_service.send_notification(
            session,
            NotificationCreate(
                user_id=log.customer_id,
                title="Negotiation accepted",
                message="The technician accepted your offer. Assignment is active.",
                notification_type="assignment",
                action_url="/dashboard/company",
            ),
        )
        tech = session.get(Technician, log.technician_id)
        if tech:
            notification_service.send_notification(
                session,
                NotificationCreate(
                    user_id=tech.user_id,
                    title="Assignment confirmed",
                    message="You have been assigned to a new workforce operation.",
                    notification_type="assignment",
                    action_url="/dashboard/worker",
                ),
            )
    elif update_in.negotiation_status == "rejected":
        job = session.get(Job, log.job_request_id)
        if job:
            job.negotiation_status = "rejected"
            session.add(job)
        notification_service.send_notification(
            session,
            NotificationCreate(
                user_id=log.customer_id,
                title="Negotiation declined",
                message="A negotiation was declined.",
                notification_type="negotiation",
                action_url="/dashboard/company",
            ),
        )

    session.add(log)
    session.commit()
    session.refresh(log)
    return log

def get_job_negotiations(session: Session, job_id: uuid.UUID) -> List[NegotiationLog]:
    return list(session.exec(
        select(NegotiationLog).where(NegotiationLog.job_request_id == job_id)
    ).all())


def _format_rate(amount: float | None, currency: str = "₹") -> str:
    if amount is None:
        return "—"
    return f"{currency}{amount:,.0f}/day"


def get_customer_negotiations(
    session: Session, customer_id: uuid.UUID
) -> List[NegotiationDashboardItem]:
    logs = list(
        session.exec(
            select(NegotiationLog)
            .where(NegotiationLog.customer_id == customer_id)
            .order_by(NegotiationLog.created_at.desc())
        ).all()
    )
    return [_enrich_negotiation(session, log) for log in logs]


def get_technician_negotiations(
    session: Session, technician_id: uuid.UUID
) -> List[NegotiationDashboardItem]:
    logs = list(
        session.exec(
            select(NegotiationLog)
            .where(NegotiationLog.technician_id == technician_id)
            .order_by(NegotiationLog.created_at.desc())
        ).all()
    )
    return [_enrich_negotiation(session, log) for log in logs]


def _enrich_negotiation(session: Session, log: NegotiationLog) -> NegotiationDashboardItem:
    job = session.get(Job, log.job_request_id)
    tech = session.get(Technician, log.technician_id)
    title = (job.required_role or job.title) if job else "Workforce Request"
    worker_name = tech.full_name if tech and tech.full_name else "Technician"
    role = tech.role if tech and tech.role else "Field Technician"
    counter = log.counter_offer or log.offered_price
    ai_rec = (
        f"Recommended settlement near {_format_rate(log.ai_recommended_price)}"
        if log.ai_recommended_price
        else "Review counter-offer against posted budget."
    )
    return NegotiationDashboardItem(
        id=log.id,
        display_code=str(log.id)[:8].upper(),
        job_request_id=log.job_request_id,
        request_title=title,
        worker_name=worker_name,
        role=role,
        original_rate=_format_rate(log.initial_price),
        counter_rate=_format_rate(counter),
        status=log.negotiation_status.replace("_", " ").title(),
        ai_recommendation=ai_rec,
        technician_id=log.technician_id,
    )
