from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.core.database import get_session
from app.core.dependencies import get_current_customer
from app.models.user import User
from app.schemas.company_schema import CompanyCreate, CompanyUpdate, CompanyResponse
from app.services import company_service

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post("/", response_model=CompanyResponse)
def create_company_profile(
    company_in: CompanyCreate,
    current_user: User = Depends(get_current_customer),
    session: Session = Depends(get_session),
):
    return company_service.create_company(session, current_user.id, company_in)


@router.get("/me", response_model=CompanyResponse)
def get_my_company_profile(
    current_user: User = Depends(get_current_customer),
    session: Session = Depends(get_session),
):
    return company_service.get_company_by_user(session, current_user.id)


@router.put("/", response_model=CompanyResponse)
def update_company_profile(
    company_in: CompanyUpdate,
    current_user: User = Depends(get_current_customer),
    session: Session = Depends(get_session),
):
    return company_service.update_company(session, current_user.id, company_in)


@router.delete("/")
def delete_company_profile(
    current_user: User = Depends(get_current_customer),
    session: Session = Depends(get_session),
):
    return company_service.delete_company(session, current_user.id)
