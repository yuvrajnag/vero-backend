from sqlmodel import SQLModel, Field, JSON, Column
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class AuditLogBase(SQLModel):
    action: str
    entity_type: str # 'user', 'job', 'payment'
    entity_id: uuid.UUID
    meta_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSON))

class AuditLog(AuditLogBase, table=True):
    __tablename__ = "audit_logs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    actor_id: Optional[uuid.UUID] = Field(foreign_key="profiles.id", default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
