from sqlmodel import SQLModel, Field, JSON, Column
from typing import Optional, Dict, Any
from datetime import datetime, date, timezone
import uuid

class AdminAnalyticsDailyBase(SQLModel):
    analytics_date: date = Field(index=True, unique=True)
    total_jobs: int = Field(default=0)
    completed_jobs: int = Field(default=0)
    cancelled_jobs: int = Field(default=0)
    active_technicians: int = Field(default=0)
    total_revenue: float = Field(default=0.0)
    total_platform_commission: float = Field(default=0.0)
    avg_job_value: float = Field(default=0.0)
    avg_completion_time_minutes: int = Field(default=0)
    emergency_jobs: int = Field(default=0)

class AdminAnalyticsDaily(AdminAnalyticsDailyBase, table=True):
    __tablename__ = "admin_analytics_daily"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PlatformMetricsBase(SQLModel):
    metric_value: float = Field(default=0.0)

class PlatformMetrics(PlatformMetricsBase, table=True):
    __tablename__ = "platform_metrics"
    metric_key: str = Field(primary_key=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TechnicianAvailabilityLogBase(SQLModel):
    status: str

class TechnicianAvailabilityLog(TechnicianAvailabilityLogBase, table=True):
    __tablename__ = "technician_availability_logs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    technician_id: uuid.UUID = Field(foreign_key="technician_profiles.id", index=True)
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
