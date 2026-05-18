from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.technician import Technician
from app.models.job import Job
from app.schemas.explain_schema import (
    ExplainRequest, ExplainSuccessResponse, ExplainPriceResponse,
    ExplainNegotiationResponse, ExplainFraudResponse, ExplainMatchResponse
)
from app.services.explainability.model_explainer import (
    explain_success, explain_price, explain_negotiation, explain_fraud, explain_match
)

router = APIRouter(prefix="/ai/explain", tags=["AI Explainability"])

@router.post("/success", response_model=ExplainSuccessResponse)
def explain_success_endpoint(
    req: ExplainRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not req.job_id:
        raise HTTPException(status_code=400, detail="job_id is required")
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    job = session.get(Job, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return explain_success(tech.model_dump(), job.model_dump(), session, str(req.technician_id))

@router.post("/pricing", response_model=ExplainPriceResponse)
def explain_pricing_endpoint(
    req: ExplainRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not req.job_id:
        raise HTTPException(status_code=400, detail="job_id is required")
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    job = session.get(Job, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return explain_price(tech.model_dump(), job.model_dump(), session, str(req.job_id))

@router.post("/negotiation", response_model=ExplainNegotiationResponse)
def explain_negotiation_endpoint(
    req: ExplainRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if req.offered_price is None:
        raise HTTPException(status_code=400, detail="offered_price is required")
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
        
    return explain_negotiation(tech.model_dump(), req.offered_price, session, str(req.technician_id))

@router.post("/fraud", response_model=ExplainFraudResponse)
def explain_fraud_endpoint(
    req: ExplainRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
        
    return explain_fraud(tech.model_dump(), session, str(req.technician_id))

@router.post("/match", response_model=ExplainMatchResponse)
def explain_match_endpoint(
    req: ExplainRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not req.job_id:
        raise HTTPException(status_code=400, detail="job_id is required")
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    job = session.get(Job, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return explain_match(tech.model_dump(), job.model_dump(), session, str(req.technician_id))
