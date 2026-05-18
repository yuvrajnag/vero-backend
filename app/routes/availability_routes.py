from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.core.database import get_session
from app.schemas.technician_schema import TechnicianResponse
from app.schemas.availability_schema import AvailabilityUpdate
from app.services import availability_service
from app.core.dependencies import get_current_technician
from app.models.user import User

router = APIRouter(prefix="/availability", tags=["Availability"])

@router.put("/", response_model=TechnicianResponse)
def update_my_availability(
    availability_in: AvailabilityUpdate,
    current_user: User = Depends(get_current_technician),
    session: Session = Depends(get_session)
):
    """Update technician availability status and location"""
    return availability_service.update_availability(session, current_user.id, availability_in)
