from pydantic import BaseModel
from typing import List, Optional
import uuid

from app.schemas.job_schema import JobResponse
from app.schemas.company_schema import CompanyResponse


class WorkforceMemberResponse(BaseModel):
    id: str
    job_request_id: uuid.UUID
    technician_id: uuid.UUID
    name: str
    role: str
    status: str
    job_status: str
    assignment: str
    duration: Optional[str] = None
    budget: Optional[float] = None


class NegotiationDashboardItem(BaseModel):
    id: uuid.UUID
    display_code: str
    job_request_id: uuid.UUID
    request_title: str
    worker_name: str
    role: str
    original_rate: str
    counter_rate: str
    status: str
    ai_recommendation: str
    technician_id: uuid.UUID


class MatchCandidateResponse(BaseModel):
    technician_id: uuid.UUID
    name: str
    role: str
    match_score: float
    experience_years: int
    rate: str
    location: Optional[str] = None
    is_online: bool = False
    skills: List[str] = []
