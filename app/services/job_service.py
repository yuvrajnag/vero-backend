from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.job import Job, JobStatus
from app.models.assignment import Assignment
from app.models.technician import Technician
from app.schemas.job_schema import JobCreate, JobUpdate
from typing import List, Optional
import uuid

def create_job(session: Session, user_id: uuid.UUID, job_in: JobCreate) -> Job:
    db_job = Job(
        customer_id=user_id,
        **job_in.model_dump()
    )
    session.add(db_job)
    session.commit()
    session.refresh(db_job)
    return db_job

def get_job(session: Session, job_id: uuid.UUID) -> Job:
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

def get_jobs(session: Session, skip: int = 0, limit: int = 100) -> List[Job]:
    return list(session.exec(select(Job).offset(skip).limit(limit)).all())

def get_jobs_by_customer(session: Session, customer_id: uuid.UUID) -> List[Job]:
    return list(
        session.exec(
            select(Job)
            .where(Job.customer_id == customer_id)
            .order_by(Job.created_at.desc())
        ).all()
    )


def get_technician_profile(session: Session, user_id: uuid.UUID) -> Optional[Technician]:
    return session.exec(select(Technician).where(Technician.user_id == user_id)).first()


def get_opportunity_jobs(session: Session) -> List[Job]:
    """Pending jobs open for technician matching."""
    return list(
        session.exec(
            select(Job)
            .where(Job.status == JobStatus.PENDING)
            .where(Job.assigned_technician_id.is_(None))
            .order_by(Job.created_at.desc())
        ).all()
    )


def get_jobs_for_technician(session: Session, user_id: uuid.UUID) -> List[Job]:
    tech = get_technician_profile(session, user_id)
    if not tech:
        return []
    return list(
        session.exec(
            select(Job)
            .where(Job.assigned_technician_id == tech.id)
            .order_by(Job.created_at.desc())
        ).all()
    )

def update_job_status(session: Session, job_id: uuid.UUID, status: JobStatus) -> Job:
    job = get_job(session, job_id)
    job.status = status
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

def assign_technician(session: Session, job_id: uuid.UUID, technician_id: uuid.UUID, caller_user_id: Optional[uuid.UUID] = None) -> Assignment:
    job = get_job(session, job_id)

    # Ownership check — company users can only assign to their own jobs
    if caller_user_id and job.customer_id != caller_user_id:
        raise HTTPException(status_code=403, detail="You can only assign technicians to your own jobs")

    # Prevent duplicate assignment
    existing = session.exec(
        select(Assignment)
        .where(Assignment.job_request_id == job_id)
        .where(Assignment.technician_id == technician_id)
    ).first()
    if existing:
        if existing.technician_id == technician_id:
            job.status = JobStatus.MATCHED
            job.assigned_technician_id = technician_id
            session.add(job)
            session.commit()
            session.refresh(existing)
            return existing
        raise HTTPException(status_code=400, detail="Technician already assigned to this job")

    new_assignment = Assignment(
        job_request_id=job_id,
        technician_id=technician_id
    )

    # Move job to MATCHED status
    job.status = JobStatus.MATCHED
    job.assigned_technician_id = technician_id
    session.add(job)
    session.add(new_assignment)
    session.commit()
    session.refresh(new_assignment)
    return new_assignment
