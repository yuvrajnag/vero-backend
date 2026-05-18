from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
import uuid

class NotificationBase(SQLModel):
    title: str
    message: str
    notification_type: str # 'job_invite', 'message', 'payment', 'system'
    is_read: bool = Field(default=False)
    action_url: Optional[str] = Field(default=None)
    meta_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSON))

class Notification(NotificationBase, table=True):
    __tablename__ = "notifications"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="profiles.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
