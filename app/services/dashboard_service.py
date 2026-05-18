from sqlmodel import Session
from app.models.job import Job, JobStatus
from app.models.technician import Technician
from app.schemas.dashboard_schema import WorkforceMemberResponse
from typing import List
import uuid


def get_workforce_for_customer(session: Session, customer_id: uuid.UUID) -> List[WorkforceMemberResponse]:
    from app.services.job_service import get_jobs_by_customer

    active_statuses = {
        JobStatus.MATCHED,
        JobStatus.NEGOTIATING,
        JobStatus.ACCEPTED,
        JobStatus.IN_PROGRESS,
    }
    jobs = get_jobs_by_customer(session, customer_id)
    members: List[WorkforceMemberResponse] = []

    for job in jobs:
        if job.status not in active_statuses or not job.assigned_technician_id:
            continue
        tech = session.get(Technician, job.assigned_technician_id)
        if not tech:
            continue
        members.append(
            WorkforceMemberResponse(
                id=str(job.id)[:8].upper(),
                job_request_id=job.id,
                technician_id=tech.id,
                name=tech.full_name or "Technician",
                role=tech.role or job.required_role or job.title,
                status=job.status.value if hasattr(job.status, "value") else str(job.status),
                job_status=job.status.value if hasattr(job.status, "value") else str(job.status),
                assignment=f"{job.title} ({job.location or 'On-site'})",
                duration=job.duration or "—",
                budget=job.final_price or job.budget,
            )
        )
    return members
