from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.notification import Notification
from app.schemas.notification_schema import NotificationCreate
from typing import List
import uuid

def send_notification(session: Session, notification_in: NotificationCreate) -> Notification:
    notification = Notification(
        user_id=notification_in.user_id,
        title=notification_in.title,
        message=notification_in.message,
        notification_type=notification_in.notification_type,
        action_url=notification_in.action_url,
        meta_data=notification_in.meta_data,
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification

def get_user_notifications(session: Session, user_id: uuid.UUID, unread_only: bool = False) -> List[Notification]:
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    return list(session.exec(query.order_by(Notification.created_at.desc()).limit(100)).all())

def mark_as_read(session: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
    notification = session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    notification.is_read = True
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification

def mark_all_as_read(session: Session, user_id: uuid.UUID) -> int:
    notifications = session.exec(
        select(Notification)
        .where(Notification.user_id == user_id)
        .where(Notification.is_read == False)
    ).all()
    for n in notifications:
        n.is_read = True
        session.add(n)
    session.commit()
    return len(notifications)
