from sqlmodel import Session, select, func
from fastapi import HTTPException
from app.models.review import TechnicianReview
from app.models.technician import Technician
from app.schemas.review_schema import ReviewCreate
from typing import List
import uuid

def create_review(session: Session, customer_id: uuid.UUID, review_in: ReviewCreate) -> TechnicianReview:
    # One review per job
    existing = session.exec(
        select(TechnicianReview).where(TechnicianReview.job_request_id == review_in.job_request_id)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Review already submitted for this job")

    review = TechnicianReview(
        job_request_id=review_in.job_request_id,
        customer_id=customer_id,
        technician_id=review_in.technician_id,
        rating=review_in.rating,
        review_text=review_in.review_text,
    )
    session.add(review)

    # Update technician aggregate rating
    _update_technician_rating(session, review_in.technician_id, review.rating)

    session.commit()
    session.refresh(review)
    return review

def get_technician_reviews(session: Session, technician_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[TechnicianReview]:
    return list(session.exec(
        select(TechnicianReview)
        .where(TechnicianReview.technician_id == technician_id)
        .offset(skip).limit(limit)
    ).all())

def get_review_by_id(session: Session, review_id: uuid.UUID) -> TechnicianReview:
    review = session.get(TechnicianReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

def flag_review(session: Session, review_id: uuid.UUID, flagged: bool = True) -> TechnicianReview:
    review = get_review_by_id(session, review_id)
    review.is_flagged = flagged
    session.add(review)
    session.commit()
    session.refresh(review)
    return review

def update_review_sentiment(session: Session, review_id: uuid.UUID, sentiment_score: float) -> TechnicianReview:
    review = get_review_by_id(session, review_id)
    review.sentiment_score = sentiment_score
    session.add(review)
    session.commit()
    session.refresh(review)
    return review

def _update_technician_rating(session: Session, technician_id: uuid.UUID, new_rating: float):
    tech = session.get(Technician, technician_id)
    if not tech:
        return
    total = tech.total_reviews
    current_avg = tech.average_rating
    tech.average_rating = round(((current_avg * total) + new_rating) / (total + 1), 2)
    tech.total_reviews = total + 1
    session.add(tech)
