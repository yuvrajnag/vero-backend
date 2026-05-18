from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.company import Company
from app.models.user import User
from app.schemas.company_schema import CompanyCreate, CompanyUpdate
from typing import List, Any
import uuid


def _company_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data)
    links = payload.get("verification_links")
    if links is not None:
        payload["verification_links"] = [
            link if isinstance(link, dict) else link
            for link in links
        ]
    return payload


def _sync_user_from_company(session: Session, user_id: uuid.UUID, payload: dict[str, Any]) -> None:
    user = session.get(User, user_id)
    if not user:
        return
    if payload.get("company_name"):
        user.full_name = payload["company_name"]
    if payload.get("email"):
        user.email = payload["email"]
    session.add(user)


def create_company(session: Session, user_id: uuid.UUID, company_in: CompanyCreate) -> Company:
    existing = session.exec(select(Company).where(Company.user_id == user_id)).first()
    payload = _company_payload(company_in.company_columns())

    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
        db_company = existing
    else:
        db_company = Company(user_id=user_id, **payload)

    session.add(db_company)
    _sync_user_from_company(session, user_id, payload)
    session.commit()
    session.refresh(db_company)
    return db_company


def get_company(session: Session, company_id: uuid.UUID) -> Company:
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


def get_company_by_user(session: Session, user_id: uuid.UUID) -> Company:
    company = session.exec(select(Company).where(Company.user_id == user_id)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return company


def update_company(session: Session, user_id: uuid.UUID, company_in: CompanyUpdate) -> Company:
    company = session.exec(select(Company).where(Company.user_id == user_id)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")

    raw = company_in.model_dump(exclude_unset=True)
    payload = _company_payload(raw)
    for key, value in payload.items():
        setattr(company, key, value)

    _sync_user_from_company(session, user_id, payload)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def delete_company(session: Session, user_id: uuid.UUID) -> dict:
    company = session.exec(select(Company).where(Company.user_id == user_id)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")

    session.delete(company)
    session.commit()
    return {"message": "Company profile deleted successfully"}
