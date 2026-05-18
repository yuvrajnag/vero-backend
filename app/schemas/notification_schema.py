from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    title: str
    message: str
    notification_type: str
    action_url: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None

class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    notification_type: str
    is_read: bool
    action_url: Optional[str]
    meta_data: Optional[Dict[str, Any]]
    created_at: datetime
