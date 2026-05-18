from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.technician import Technician
from app.models.job import Job
from app.models.ai import AIRecommendationLog
from app.schemas.ai_schema import (
    SkillMatchRequest, SkillMatchResponse, TechnicianMatchResult,
    SuccessProbRequest, SuccessProbResponse,
    PricePredictRequest, PricePredictResponse,
    NegotiationPredictRequest, NegotiationPredictResponse,
    SentimentRequest, SentimentResponse,
    FraudScanRequest, FraudScanResponse,
)
from app.services.ai import skill_matcher, success_predictor, price_predictor
from app.services.ai import negotiation_predictor, sentiment_analyzer, fraud_detector
from app.services import review_service, fraud_service
import uuid

router = APIRouter(prefix="/ai", tags=["AI"])


# ── Skill Matching ───────────────────────────────────────────────────

@router.post("/match", response_model=SkillMatchResponse)
def match_technicians(
    req: SkillMatchRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Rank technicians by skill match for a given job."""
    job = session.get(Job, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        technicians = list(session.exec(select(Technician).where(Technician.is_online == True)).all())

        tech_dicts = [
            {
                "id": str(t.id),
                "skills": t.skills or [],
                "experience_years": t.experience_years,
                "average_rating": t.average_rating,
                "is_online": t.is_online,
            }
            for t in technicians
        ]

        ranked = skill_matcher.rank_technicians(job.required_skills or [], tech_dicts, top_k=req.top_k)

        # Persist match scores to AIRecommendationLog
        for rank_i, r in enumerate(ranked):
            log = AIRecommendationLog(
                job_request_id=job.id,
                technician_id=uuid.UUID(r["id"]),
                ai_match_score=r["match_score"],
                recommendation_rank=rank_i + 1,
            )
            session.add(log)
        session.commit()

        results = [
            TechnicianMatchResult(
                technician_id=uuid.UUID(r["id"]),
                match_score=r["match_score"],
                skills=r["skills"],
                experience_years=r["experience_years"],
                average_rating=r["average_rating"],
                is_online=r["is_online"],
            )
            for r in ranked
        ]
        return SkillMatchResponse(job_id=req.job_id, matches=results)
    except Exception as e:
        import logging
        logging.error(f"Fallback match failed: {e}")
        return SkillMatchResponse(job_id=req.job_id, matches=[])


# ── Success Probability ──────────────────────────────────────────────

@router.post("/success-probability", response_model=SuccessProbResponse)
def predict_success(
    req: SuccessProbRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Predict probability that a technician completes a job successfully."""
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    job = session.get(Job, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tech_dict = tech.model_dump()
    job_dict = job.model_dump()
    prob = success_predictor.predict_success_probability(tech_dict, job_dict)

    return SuccessProbResponse(
        technician_id=req.technician_id,
        job_id=req.job_id,
        success_probability=prob,
    )


# ── Fair Price Prediction ────────────────────────────────────────────

@router.post("/price-prediction", response_model=PricePredictResponse)
def predict_price(
    req: PricePredictRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Predict a fair market price for a job + technician combination."""
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    job = session.get(Job, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = price_predictor.predict_fair_price(tech.model_dump(), job.model_dump())
    return PricePredictResponse(
        technician_id=req.technician_id,
        job_id=req.job_id,
        **result,
    )


# ── Negotiation Acceptance ───────────────────────────────────────────

@router.post("/negotiation-probability", response_model=NegotiationPredictResponse)
def predict_negotiation(
    req: NegotiationPredictRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Predict whether a technician will accept an offered price."""
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    result = negotiation_predictor.predict_acceptance_probability(
        tech.model_dump(), req.offered_price
    )
    return NegotiationPredictResponse(
        technician_id=req.technician_id,
        offered_price=req.offered_price,
        **result,
    )


# ── Sentiment Analysis ───────────────────────────────────────────────

@router.post("/sentiment", response_model=SentimentResponse)
def analyze_review_sentiment(
    req: SentimentRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Analyze sentiment of review text and optionally update the review record."""
    result = sentiment_analyzer.analyze_sentiment(req.text)

    if req.review_id:
        review_service.update_review_sentiment(session, req.review_id, result["sentiment_score"])
        if result["is_toxic"]:
            review_service.flag_review(session, req.review_id, flagged=True)

    return SentimentResponse(
        sentiment_score=result["sentiment_score"],
        label=result["label"],
        is_toxic=result["is_toxic"],
    )


# ── Fraud Risk Scan ──────────────────────────────────────────────────

@router.post("/fraud-scan", response_model=FraudScanResponse)
def scan_fraud_risk(
    req: FraudScanRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Run fraud risk analysis on a technician and persist the result."""
    tech = session.get(Technician, req.technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    result = fraud_detector.compute_fraud_risk(tech.model_dump())

    # Auto-log high-risk detections
    if result["risk_score"] >= 0.70:
        fraud_service.log_fraud_event(
            session,
            technician_id=req.technician_id,
            risk_score=result["risk_score"],
            fraud_reason=result["reason"],
        )

    return FraudScanResponse(
        technician_id=req.technician_id,
        **result,
    )
