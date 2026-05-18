from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

from app.schemas.common_schema import VerificationLink


class CompanyOnboardingFields(BaseModel):
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=15)
    address: Optional[str] = None
    hq_location: Optional[str] = None
    logo_url: Optional[str] = None

    industry: Optional[str] = None
    other_industry: Optional[str] = None
    company_size: Optional[str] = None
    business_categories: List[str] = []
    website_url: Optional[str] = None
    operating_regions: List[str] = []
    about: Optional[str] = None

    preferred_workforce_types: List[str] = []
    hiring_frequency: Optional[str] = None
    remote_pref: Optional[str] = None
    urgency_handling: Optional[str] = None
    verification_requirements: List[str] = []
    currency: Optional[str] = None
    project_budget: Optional[float] = None

    current_team_size: Optional[int] = None
    active_projects_count: Optional[int] = None
    workforce_goals: List[str] = []
    assignment_workflow: Optional[str] = None
    communication_preferences: List[str] = []
    notification_settings: Optional[str] = None

    registration_doc_url: Optional[str] = None
    tax_docs_url: Optional[str] = None
    identity_verification_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    authorized_rep_name: Optional[str] = None
    verification_links: List[VerificationLink] = []

    hiring_preferences: Optional[str] = None

    def company_columns(self) -> dict:
        data = self.model_dump(exclude_none=True)
        links = data.get("verification_links")
        if links is not None:
            data["verification_links"] = [
                item if isinstance(item, dict) else item.model_dump()
                for item in links
            ]
        return data


class CompanyCreate(CompanyOnboardingFields):
    company_name: str = Field(min_length=2)
    email: str


class CompanyUpdate(CompanyOnboardingFields):
    pass


class CompanyResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    hq_location: Optional[str] = None
    logo_url: Optional[str] = None
    industry: Optional[str] = None
    other_industry: Optional[str] = None
    company_size: Optional[str] = None
    business_categories: List[str] = []
    website_url: Optional[str] = None
    operating_regions: List[str] = []
    about: Optional[str] = None
    preferred_workforce_types: List[str] = []
    hiring_frequency: Optional[str] = None
    remote_pref: Optional[str] = None
    urgency_handling: Optional[str] = None
    verification_requirements: List[str] = []
    currency: Optional[str] = None
    project_budget: Optional[float] = None
    current_team_size: Optional[int] = None
    active_projects_count: Optional[int] = None
    workforce_goals: List[str] = []
    assignment_workflow: Optional[str] = None
    communication_preferences: List[str] = []
    notification_settings: Optional[str] = None
    registration_doc_url: Optional[str] = None
    tax_docs_url: Optional[str] = None
    identity_verification_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    authorized_rep_name: Optional[str] = None
    verification_links: List[dict] = []
    hiring_preferences: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
