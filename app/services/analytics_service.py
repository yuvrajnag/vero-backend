from sqlmodel import Session, select, func
from app.models.analytics import AdminAnalyticsDaily, PlatformMetrics
from app.models.job import Job, JobStatus
from app.models.technician import Technician
from app.models.payment import Payment
from app.models.review import TechnicianReview
from app.models.fraud import FraudDetectionLog
from datetime import date, datetime, timezone
from typing import Optional
import uuid

def get_daily_analytics(session: Session, analytics_date: Optional[date] = None) -> AdminAnalyticsDaily:
    target = analytics_date or date.today()
    row = session.exec(
        select(AdminAnalyticsDaily).where(AdminAnalyticsDaily.analytics_date == target)
    ).first()
    if not row:
        row = _compute_daily(session, target)
    return row

def get_platform_metrics(session: Session) -> dict:
    metrics = session.exec(select(PlatformMetrics)).all()
    return {m.metric_key: m.metric_value for m in metrics}

def aggregate_metrics(session: Session) -> AdminAnalyticsDaily:
    """Called by background task to recompute today's analytics."""
    return _compute_daily(session, date.today(), upsert=True)

def _compute_daily(session: Session, target: date, upsert: bool = False) -> AdminAnalyticsDaily:
    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    end = datetime(target.year, target.month, target.day, 23, 59, 59, tzinfo=timezone.utc)

    total_jobs = session.exec(
        select(func.count(Job.id)).where(Job.created_at >= start, Job.created_at <= end)
    ).one() or 0

    completed_jobs = session.exec(
        select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED, Job.created_at >= start, Job.created_at <= end)
    ).one() or 0

    cancelled_jobs = session.exec(
        select(func.count(Job.id)).where(Job.status == JobStatus.CANCELLED, Job.created_at >= start, Job.created_at <= end)
    ).one() or 0

    emergency_jobs = session.exec(
        select(func.count(Job.id)).where(Job.urgency_level == "emergency", Job.created_at >= start, Job.created_at <= end)
    ).one() or 0

    active_technicians = session.exec(
        select(func.count(Technician.id)).where(Technician.is_online == True)
    ).one() or 0

    revenue_result = session.exec(
        select(func.sum(Payment.amount)).where(
            Payment.payment_status == "completed",
            Payment.created_at >= start,
            Payment.created_at <= end
        )
    ).one()
    total_revenue = float(revenue_result or 0.0)

    commission_result = session.exec(
        select(func.sum(Payment.platform_fee)).where(
            Payment.payment_status == "completed",
            Payment.created_at >= start,
            Payment.created_at <= end
        )
    ).one()
    total_commission = float(commission_result or 0.0)

    avg_job_value = round(total_revenue / completed_jobs, 2) if completed_jobs else 0.0

    existing = session.exec(
        select(AdminAnalyticsDaily).where(AdminAnalyticsDaily.analytics_date == target)
    ).first()

    if existing and upsert:
        existing.total_jobs = total_jobs
        existing.completed_jobs = completed_jobs
        existing.cancelled_jobs = cancelled_jobs
        existing.active_technicians = active_technicians
        existing.total_revenue = total_revenue
        existing.total_platform_commission = total_commission
        existing.avg_job_value = avg_job_value
        existing.emergency_jobs = emergency_jobs
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    row = AdminAnalyticsDaily(
        analytics_date=target,
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        cancelled_jobs=cancelled_jobs,
        active_technicians=active_technicians,
        total_revenue=total_revenue,
        total_platform_commission=total_commission,
        avg_job_value=avg_job_value,
        emergency_jobs=emergency_jobs,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row

def upsert_platform_metric(session: Session, key: str, value: float):
    metric = session.get(PlatformMetrics, key)
    if metric:
        metric.metric_value = value
        metric.updated_at = datetime.now(timezone.utc)
    else:
        metric = PlatformMetrics(metric_key=key, metric_value=value)
    session.add(metric)
    session.commit()
