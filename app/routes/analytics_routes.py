from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import Optional
from datetime import date
from app.core.database import get_session
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/daily")
def get_daily_analytics(
    report_date: Optional[date] = Query(default=None, description="ISO date e.g. 2025-05-17"),
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Daily aggregated platform analytics. Defaults to today."""
    result = analytics_service.get_daily_analytics(session, report_date)
    return result


@router.post("/aggregate")
def trigger_aggregation(
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Manually trigger today's analytics aggregation (idempotent)."""
    result = analytics_service.aggregate_metrics(session)
    return result


@router.get("/metrics")
def get_platform_metrics(
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Live key-value platform metrics."""
    return analytics_service.get_platform_metrics(session)
