from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import List
from app.core.database import get_session
from app.core.dependencies import get_current_user, get_current_admin
from app.models.user import User
from app.schemas.review_schema import ReviewCreate, ReviewResponse
from app.services import review_service
from app.services.ai import sentiment_analyzer
import uuid

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewResponse)
def submit_review(
    review_in: ReviewCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Submit a review for a completed job. Automatically runs sentiment analysis."""
    review = review_service.create_review(session, current_user.id, review_in)

    # Auto-analyze sentiment if review text provided
    if review.review_text:
        result = sentiment_analyzer.analyze_sentiment(review.review_text)
        review = review_service.update_review_sentiment(session, review.id, result["sentiment_score"])
        if result["is_toxic"]:
            review = review_service.flag_review(session, review.id, flagged=True)

    return review


@router.get("/technician/{technician_id}", response_model=List[ReviewResponse])
def get_technician_reviews(
    technician_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session),
):
    """Get all reviews for a technician."""
    return review_service.get_technician_reviews(session, technician_id, skip, limit)


@router.post("/{review_id}/flag")
def flag_review(
    review_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Admin: manually flag a review."""
    return review_service.flag_review(session, review_id, flagged=True)


@router.post("/{review_id}/unflag")
def unflag_review(
    review_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    """Admin: remove flag from a review."""
    return review_service.flag_review(session, review_id, flagged=False)
