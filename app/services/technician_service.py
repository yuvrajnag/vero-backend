from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.technician import Technician
from app.models.user import User
from app.schemas.technician_schema import TechnicianCreate, TechnicianUpdate
from typing import List, Any
import uuid


def _onboarding_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data)
    if payload.get("daily_rate") is None and payload.get("base_hourly_rate") is not None:
        payload["daily_rate"] = payload["base_hourly_rate"]
    payload.pop("base_hourly_rate", None)

    emergency = payload.get("emergency_availability")
    if emergency is not None:
        payload["is_emergency_available"] = str(emergency).strip().lower() == "yes"

    links = payload.get("verification_links")
    if links is not None:
        payload["verification_links"] = [
            link if isinstance(link, dict) else link
            for link in links
        ]
    return payload


def _sync_user_from_profile(session: Session, user_id: uuid.UUID, payload: dict[str, Any]) -> None:
    user = session.get(User, user_id)
    if not user:
        return
    if payload.get("full_name"):
        user.full_name = payload["full_name"]
    if payload.get("email"):
        user.email = payload["email"]
    session.add(user)


def _save_technician_profile(
    session: Session,
    user_id: uuid.UUID,
    payload: dict[str, Any],
) -> Technician:
    tech = session.exec(select(Technician).where(Technician.user_id == user_id)).first()
    normalized = _onboarding_payload(payload)

    if tech:
        for key, value in normalized.items():
            setattr(tech, key, value)
    else:
        tech = Technician(user_id=user_id, **normalized)
        session.add(tech)

    _sync_user_from_profile(session, user_id, normalized)
    session.commit()
    session.refresh(tech)
    return tech


def create_technician(session: Session, user_id: uuid.UUID, tech_in: TechnicianCreate) -> Technician:
    """Create or update technician profile (idempotent for onboarding retries)."""
    return _save_technician_profile(session, user_id, tech_in.technician_columns())


def get_technician(session: Session, tech_id: uuid.UUID) -> Technician:
    tech = session.get(Technician, tech_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    return tech


def get_technician_by_user(session: Session, user_id: uuid.UUID) -> Technician:
    tech = session.exec(select(Technician).where(Technician.user_id == user_id)).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician profile not found")
    return tech


def get_technicians(session: Session, skip: int = 0, limit: int = 100) -> List[Technician]:
    return list(session.exec(select(Technician).offset(skip).limit(limit)).all())


def update_technician(session: Session, user_id: uuid.UUID, tech_in: TechnicianUpdate) -> Technician:
    """Update or create technician profile if missing (profile edit / recovery)."""
    raw = tech_in.model_dump(exclude_unset=True)
    return _save_technician_profile(session, user_id, raw)


def delete_technician(session: Session, user_id: uuid.UUID) -> dict:
    tech = session.exec(select(Technician).where(Technician.user_id == user_id)).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician profile not found")

    session.delete(tech)
    session.commit()
    return {"message": "Technician profile deleted successfully"}
