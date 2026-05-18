from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List
from app.core.database import get_session
from app.schemas.job_schema import JobCreate, JobResponse
from app.models.job import JobStatus
from app.services import job_service
from app.core.dependencies import (
    get_current_active_user,
    get_current_admin,
    get_current_technician,
)
from app.schemas.dashboard_schema import WorkforceMemberResponse
from app.services import dashboard_service
from app.models.user import User
import uuid

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/", response_model=JobResponse)
def create_job_request(
    job_in: JobCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Create a new job request"""
    return job_service.create_job(session, current_user.id, job_in)

@router.get("/", response_model=List[JobResponse])
def get_all_jobs(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """Get all jobs"""
    return job_service.get_jobs(session, skip, limit)


@router.get("/me", response_model=List[JobResponse])
def get_my_jobs(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Jobs created by the authenticated company user."""
    return job_service.get_jobs_by_customer(session, current_user.id)


@router.get("/me/workforce", response_model=List[WorkforceMemberResponse])
def get_my_workforce(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Assigned technicians for the authenticated company's active jobs."""
    return dashboard_service.get_workforce_for_customer(session, current_user.id)


@router.get("/opportunities", response_model=List[JobResponse])
def get_opportunity_jobs(
    current_user: User = Depends(get_current_technician),
    session: Session = Depends(get_session),
):
    """Open pending jobs for technician discovery."""
    return job_service.get_opportunity_jobs(session)


@router.get("/assignments/me", response_model=List[JobResponse])
def get_my_assignments(
    current_user: User = Depends(get_current_technician),
    session: Session = Depends(get_session),
):
    """Jobs assigned to the authenticated technician."""
    return job_service.get_jobs_for_technician(session, current_user.id)

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, session: Session = Depends(get_session)):
    """Get job details by ID"""
    return job_service.get_job(session, job_id)

@router.put("/{job_id}/status", response_model=JobResponse)
def update_job_status(
    job_id: uuid.UUID,
    status: JobStatus,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Update job status"""
    return job_service.update_job_status(session, job_id, status)

@router.post("/{job_id}/assign/{technician_id}")
def assign_technician_to_job(
    job_id: uuid.UUID,
    technician_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Assign a technician to a job. Company users can only assign to their own jobs."""
    return job_service.assign_technician(session, job_id, technician_id, current_user.id)
