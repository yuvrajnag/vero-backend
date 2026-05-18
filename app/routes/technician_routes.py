from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List
from app.core.database import get_session
from app.schemas.technician_schema import TechnicianCreate, TechnicianUpdate, TechnicianResponse
from app.services import technician_service
from app.core.dependencies import get_current_active_user, get_current_technician
from app.models.user import User
import uuid

router = APIRouter(prefix="/technicians", tags=["Technicians"])

@router.post("/", response_model=TechnicianResponse)
def create_technician_profile(
    tech_in: TechnicianCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Create a technician profile (onboarding — any active user without a profile yet)."""
    return technician_service.create_technician(session, current_user.id, tech_in)

@router.get("/", response_model=List[TechnicianResponse])
def get_all_technicians(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """Get all technicians"""
    return technician_service.get_technicians(session, skip, limit)

@router.get("/me", response_model=TechnicianResponse)
def get_my_technician_profile(
    current_user: User = Depends(get_current_technician),
    session: Session = Depends(get_session),
):
    """Get the authenticated technician's profile"""
    return technician_service.get_technician_by_user(session, current_user.id)


@router.get("/{tech_id}", response_model=TechnicianResponse)
def get_technician(tech_id: uuid.UUID, session: Session = Depends(get_session)):
    """Get technician details by ID"""
    return technician_service.get_technician(session, tech_id)

@router.put("/", response_model=TechnicianResponse)
def update_technician_profile(
    tech_in: TechnicianUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Update technician profile for the current user (creates profile if missing)."""
    return technician_service.update_technician(session, current_user.id, tech_in)

@router.delete("/")
def delete_technician_profile(
    current_user: User = Depends(get_current_technician),
    session: Session = Depends(get_session)
):
    """Delete technician profile for the current user"""
    return technician_service.delete_technician(session, current_user.id)
