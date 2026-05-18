from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List
import uuid

from app.core.database import get_session
from app.core.dependencies import get_current_technician
from app.models.user import User
from app.schemas.technician_portfolio_schema import (
    TechnicianPortfolioCreate,
    TechnicianPortfolioUpdate,
    TechnicianPortfolioResponse,
)
from app.services import portfolio_service

router = APIRouter(prefix="/technicians/portfolio", tags=["Technician Portfolio"])


@router.post("/", response_model=TechnicianPortfolioResponse)
def create_portfolio_entry(
    entry_in: TechnicianPortfolioCreate,
    current_user: User = Depends(get_current_technician),
    session: Session = Depends(get_session),
):
    return portfolio_service.create_portfolio_entry(session, current_user.id, entry_in)


@router.get("/", response_model=List[TechnicianPortfolioResponse])
def list_portfolio_entries(
    current_user: User = Depends(get_current_technician),
    session: Session = Depends(get_session),
):
    return portfolio_service.list_portfolio_entries(session, current_user.id)


@router.put("/{entry_id}", response_model=TechnicianPortfolioResponse)
def update_portfolio_entry(
    entry_id: uuid.UUID,
    entry_in: TechnicianPortfolioUpdate,
    current_user: User = Depends(get_current_technician),
    session: Session = Depends(get_session),
):
    return portfolio_service.update_portfolio_entry(
        session, current_user.id, entry_id, entry_in
    )


@router.delete("/{entry_id}")
def delete_portfolio_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_technician),
    session: Session = Depends(get_session),
):
    return portfolio_service.delete_portfolio_entry(session, current_user.id, entry_id)
