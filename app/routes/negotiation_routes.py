from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.negotiation_schema import NegotiationCreate, NegotiationUpdate, NegotiationResponse
from app.schemas.dashboard_schema import NegotiationDashboardItem
from app.services import negotiation_service, job_service
from app.core.dependencies import get_current_customer, get_current_technician
from app.models.user import UserRole, normalize_role
import uuid

router = APIRouter(prefix="/negotiations", tags=["Negotiations"])


@router.post("/", response_model=NegotiationResponse)
def start_negotiation(
    negotiation_in: NegotiationCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Start a price negotiation on a job."""
    return negotiation_service.create_negotiation(session, negotiation_in)


@router.put("/{negotiation_id}", response_model=NegotiationResponse)
def update_negotiation(
    negotiation_id: uuid.UUID,
    update_in: NegotiationUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update a negotiation — submit counter-offer, accept, or reject."""
    return negotiation_service.update_negotiation(session, negotiation_id, update_in)


@router.get("/job/{job_id}", response_model=List[NegotiationResponse])
def get_job_negotiations(
    job_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all negotiation logs for a job."""
    return negotiation_service.get_job_negotiations(session, job_id)


@router.get("/me", response_model=List[NegotiationDashboardItem])
def get_my_negotiations(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Negotiations for the current customer or technician."""
    role = normalize_role(current_user.role)
    if role == UserRole.TECHNICIAN:
        tech = job_service.get_technician_profile(session, current_user.id)
        if not tech:
            return []
        return negotiation_service.get_technician_negotiations(session, tech.id)
    return negotiation_service.get_customer_negotiations(session, current_user.id)
