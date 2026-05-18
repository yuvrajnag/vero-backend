from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import List
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification_schema import NotificationCreate, NotificationResponse
from app.services import notification_service
import uuid

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationResponse])
def get_my_notifications(
    unread_only: bool = Query(default=False),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all notifications for the current user."""
    return notification_service.get_user_notifications(session, current_user.id, unread_only)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Mark a single notification as read."""
    return notification_service.mark_as_read(session, notification_id, current_user.id)


@router.post("/read-all")
def mark_all_read(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read for current user."""
    count = notification_service.mark_all_as_read(session, current_user.id)
    return {"marked_read": count}
