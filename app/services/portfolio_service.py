from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.technician import Technician
from app.models.technician_portfolio import TechnicianPortfolioEntry
from app.schemas.technician_portfolio_schema import (
    TechnicianPortfolioCreate,
    TechnicianPortfolioUpdate,
)
from typing import List
import uuid


def _get_technician_for_user(session: Session, user_id: uuid.UUID) -> Technician:
    tech = session.exec(select(Technician).where(Technician.user_id == user_id)).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician profile not found")
    return tech


def create_portfolio_entry(
    session: Session,
    user_id: uuid.UUID,
    entry_in: TechnicianPortfolioCreate,
) -> TechnicianPortfolioEntry:
    tech = _get_technician_for_user(session, user_id)
    entry = TechnicianPortfolioEntry(technician_id=tech.id, **entry_in.model_dump())
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def list_portfolio_entries(
    session: Session, user_id: uuid.UUID
) -> List[TechnicianPortfolioEntry]:
    tech = _get_technician_for_user(session, user_id)
    return list(
        session.exec(
            select(TechnicianPortfolioEntry).where(
                TechnicianPortfolioEntry.technician_id == tech.id
            )
        ).all()
    )


def update_portfolio_entry(
    session: Session,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    entry_in: TechnicianPortfolioUpdate,
) -> TechnicianPortfolioEntry:
    tech = _get_technician_for_user(session, user_id)
    entry = session.get(TechnicianPortfolioEntry, entry_id)
    if not entry or entry.technician_id != tech.id:
        raise HTTPException(status_code=404, detail="Portfolio entry not found")

    for key, value in entry_in.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)

    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def delete_portfolio_entry(
    session: Session, user_id: uuid.UUID, entry_id: uuid.UUID
) -> dict:
    tech = _get_technician_for_user(session, user_id)
    entry = session.get(TechnicianPortfolioEntry, entry_id)
    if not entry or entry.technician_id != tech.id:
        raise HTTPException(status_code=404, detail="Portfolio entry not found")

    session.delete(entry)
    session.commit()
    return {"message": "Portfolio entry deleted successfully"}
