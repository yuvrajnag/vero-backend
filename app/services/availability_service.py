from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.technician import Technician
from app.models.analytics import TechnicianAvailabilityLog
from app.schemas.availability_schema import AvailabilityUpdate
from datetime import datetime, timezone
import uuid

def update_availability(session: Session, user_id: uuid.UUID, availability_in: AvailabilityUpdate) -> Technician:
    tech = session.exec(select(Technician).where(Technician.user_id == user_id)).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician profile not found")

    prev_status = tech.current_status
    tech.is_online = availability_in.is_online
    tech.current_status = availability_in.current_status or ("online" if availability_in.is_online else "offline")
    tech.last_seen_at = datetime.now(timezone.utc)

    if availability_in.latitude is not None:
        tech.latitude = availability_in.latitude
    if availability_in.longitude is not None:
        tech.longitude = availability_in.longitude
    if availability_in.custom_status_message is not None:
        tech.custom_status_message = availability_in.custom_status_message

    # Log availability change
    if prev_status != tech.current_status:
        log = TechnicianAvailabilityLog(technician_id=tech.id, status=tech.current_status)
        session.add(log)

    session.add(tech)
    session.commit()
    session.refresh(tech)
    return tech
