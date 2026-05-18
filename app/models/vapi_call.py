"""
VapiCall Model
--------------
Tracks every AI voice call placed by the auto-assign system via Vapi.
Each row = one call attempt to one technician for one job.

States:
  initiated  → call triggered via Vapi REST API
  in_progress→ call connected (webhook: call-started)
  accepted   → technician agreed during call (webhook: end-of-call-report)
  rejected   → technician declined
  no_answer  → call not answered / voicemail
  failed     → Vapi/Twilio error
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


class VapiCall(SQLModel, table=True):
    __tablename__ = "vapi_calls"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="job_requests.id", index=True)
    technician_id: uuid.UUID = Field(foreign_key="technician_profiles.id", index=True)

    rank: int = Field(default=0)                  # position in the ranked list (1 = top)
    vapi_call_id: Optional[str] = Field(default=None, max_length=255)  # Vapi's own call_id

    status: str = Field(default="initiated", max_length=50)
    # initiated | in_progress | accepted | rejected | no_answer | failed

    # Negotiation outcome
    agreed_price: Optional[float] = Field(default=None)
    call_summary: Optional[str] = Field(default=None)       # Vapi end-of-call transcript summary
    raw_transcript: Optional[str] = Field(default=None)     # full transcript if captured

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
