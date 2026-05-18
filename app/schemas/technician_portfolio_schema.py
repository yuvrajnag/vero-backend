from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime


class TechnicianPortfolioCreate(BaseModel):
    operation_title: str = Field(min_length=1, max_length=255)
    scope_of_work: Optional[str] = None
    technical_role: Optional[str] = None
    commercial_client: Optional[str] = None
    completion_year: Optional[str] = Field(default=None, max_length=10)
    skills_certifications_applied: List[str] = []
    proof_image_url: Optional[str] = None
    registry_verification_url: Optional[str] = None
    is_featured: bool = False


class TechnicianPortfolioUpdate(BaseModel):
    operation_title: Optional[str] = Field(default=None, max_length=255)
    scope_of_work: Optional[str] = None
    technical_role: Optional[str] = None
    commercial_client: Optional[str] = None
    completion_year: Optional[str] = Field(default=None, max_length=10)
    skills_certifications_applied: Optional[List[str]] = None
    proof_image_url: Optional[str] = None
    registry_verification_url: Optional[str] = None
    is_featured: Optional[bool] = None


class TechnicianPortfolioResponse(BaseModel):
    id: uuid.UUID
    technician_id: uuid.UUID
    operation_title: str
    scope_of_work: Optional[str] = None
    technical_role: Optional[str] = None
    commercial_client: Optional[str] = None
    completion_year: Optional[str] = None
    skills_certifications_applied: List[str] = []
    proof_image_url: Optional[str] = None
    registry_verification_url: Optional[str] = None
    is_featured: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
