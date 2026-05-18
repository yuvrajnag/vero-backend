from sqlmodel import Session, select, func
from fastapi import HTTPException
from app.models.user import User
from app.models.technician import Technician
from app.models.job import Job, JobStatus
from app.models.fraud import FraudDetectionLog
from app.models.audit import AuditLog
from app.models.analytics import AdminAnalyticsDaily
from typing import List, Optional
import uuid
from datetime import datetime, timezone, date

# ── User management ──────────────────────────────────────────────────

def get_all_users(session: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return list(session.exec(select(User).offset(skip).limit(limit)).all())

def deactivate_user(session: Session, user_id: uuid.UUID, admin_id: uuid.UUID) -> User:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    session.add(user)
    _write_audit(session, admin_id, "deactivate_user", "user", user_id)
    session.commit()
    session.refresh(user)
    return user

def verify_technician(session: Session, technician_id: uuid.UUID, admin_id: uuid.UUID) -> Technician:
    tech = session.get(Technician, technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    tech.is_background_verified = True
    tech.verification_level = "verified"
    session.add(tech)
    _write_audit(session, admin_id, "verify_technician", "technician", technician_id)
    session.commit()
    session.refresh(tech)
    return tech

# ── Audit logs ────────────────────────────────────────────────────────

def get_audit_logs(session: Session, skip: int = 0, limit: int = 100) -> List[AuditLog]:
    return list(session.exec(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    ).all())

def _write_audit(session: Session, actor_id: uuid.UUID, action: str, entity_type: str, entity_id: uuid.UUID):
    log = AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id)
    session.add(log)

# ── Dashboard summary ─────────────────────────────────────────────────

def get_dashboard_summary(session: Session) -> dict:
    total_users = session.exec(select(func.count(User.id))).one() or 0
    total_technicians = session.exec(select(func.count(Technician.id))).one() or 0
    active_technicians = session.exec(
        select(func.count(Technician.id)).where(Technician.is_online == True)
    ).one() or 0
    total_jobs = session.exec(select(func.count(Job.id))).one() or 0
    open_jobs = session.exec(
        select(func.count(Job.id)).where(Job.status == JobStatus.PENDING)
    ).one() or 0
    open_fraud_flags = session.exec(
        select(func.count(FraudDetectionLog.id)).where(FraudDetectionLog.resolved_at == None)
    ).one() or 0

    return {
        "total_users": total_users,
        "total_technicians": total_technicians,
        "active_technicians": active_technicians,
        "total_jobs": total_jobs,
        "open_jobs": open_jobs,
        "open_fraud_flags": open_fraud_flags,
    }

def get_technician_performance(session: Session, limit: int = 20) -> List[dict]:
    techs = session.exec(
        select(Technician).order_by(Technician.average_rating.desc()).limit(limit)
    ).all()
    return [
        {
            "id": str(t.id),
            "full_name": t.full_name,
            "average_rating": t.average_rating,
            "total_jobs_completed": t.total_jobs_completed,
            "success_score": t.success_score,
            "fraud_risk_score": t.fraud_risk_score,
            "completion_rate": t.completion_rate,
            "verification_level": t.verification_level,
        }
        for t in techs
    ]
