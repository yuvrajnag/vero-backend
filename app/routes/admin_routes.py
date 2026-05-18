from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import List, Optional
from datetime import date
from app.core.database import get_session
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.models.fraud import FraudDetectionLog
from app.models.audit import AuditLog
from app.services import admin_service, fraud_service, analytics_service
from app.schemas.technician_schema import TechnicianResponse
import uuid

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
def get_dashboard(
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Platform-wide dashboard summary."""
    return admin_service.get_dashboard_summary(session)


@router.get("/users")
def list_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """List all registered users."""
    users = admin_service.get_all_users(session, skip, limit)
    return users


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Deactivate a user account."""
    return admin_service.deactivate_user(session, user_id, current_admin.id)


@router.post("/technicians/{technician_id}/verify", response_model=TechnicianResponse)
def verify_technician(
    technician_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Mark a technician as background-verified."""
    return admin_service.verify_technician(session, technician_id, current_admin.id)


@router.get("/technicians/performance")
def technician_performance(
    limit: int = 20,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Ranked technician performance report."""
    return admin_service.get_technician_performance(session, limit)


@router.get("/fraud-logs")
def get_fraud_logs(
    resolved: Optional[bool] = Query(default=None),
    limit: int = 100,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """List fraud detection logs. Filter by resolved status."""
    return fraud_service.get_fraud_logs(session, resolved=resolved, limit=limit)


@router.post("/fraud-logs/{event_id}/resolve")
def resolve_fraud(
    event_id: uuid.UUID,
    action_taken: str,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Resolve a fraud detection event."""
    return fraud_service.resolve_fraud_event(session, event_id, current_admin.id, action_taken)


@router.get("/audit-logs")
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Retrieve platform audit trail."""
    return admin_service.get_audit_logs(session, skip, limit)
