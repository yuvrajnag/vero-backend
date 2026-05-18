from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, date
import uuid

class AnalyticsDailyResponse(BaseModel):
    id: uuid.UUID
    report_date: date
    total_revenue: float
    platform_commission: float
    active_technicians: int
    jobs_completed: int
    jobs_cancelled: int
    emergency_jobs: int
    average_rating: float
    fraud_flags: int
    metrics_json: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

class PlatformMetricsResponse(BaseModel):
    id: uuid.UUID
    metric_name: str
    metric_value: float
    metadata: Optional[Dict[str, Any]]
    recorded_at: datetime
