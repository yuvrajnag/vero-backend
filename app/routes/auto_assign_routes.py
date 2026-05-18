"""
Auto-Assign Routes (Polling Mode — no webhooks required)
---------------------------------------------------------
Endpoints:
  POST /auto-assign/{job_id}        — Start ranked AI calling campaign
  GET  /auto-assign/{job_id}/status — Poll campaign status
  POST /auto-assign/webhook/vapi    — Optional: Vapi webhook (kept for production use)

How it works WITHOUT webhooks:
  1. Company triggers /auto-assign/{job_id} with ranked technician list.
  2. Backend places a Vapi call to Rank #1 technician in a background thread.
  3. Background thread polls GET /call/{id} every 8 seconds until call ends.
  4. Once ended, reads summary/transcript to determine outcome:
       - accepted  → auto-assign technician, campaign done.
       - rejected / no_answer → call Rank #2, then #3 etc.
  5. Frontend polls GET /auto-assign/{job_id}/status every 5s to show live log.

No ngrok, no public URL needed for local development.
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session, engine
from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.models.job import Job, JobStatus
from app.models.technician import Technician
from app.models.user import User
from app.models.vapi_call import VapiCall
from app.services import job_service, vapi_service, twilio_service
from app.utils.logger import logger

router = APIRouter(prefix="/auto-assign", tags=["Auto Assign"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class AutoAssignRequest(BaseModel):
    """Ranked technicians sent from the frontend after AI matching."""
    technicians: List[Dict[str, Any]]


class CallStatusResponse(BaseModel):
    job_id: str
    status: str   # idle | calling | completed | exhausted
    calls: List[Dict[str, Any]]
    assigned_technician_id: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_technician_by_id(session: Session, tech_id: str) -> Optional[Technician]:
    try:
        uid = uuid.UUID(tech_id)
    except ValueError:
        return None
    return session.get(Technician, uid)


def _record_call(
    session: Session,
    job_id: uuid.UUID,
    tech_id: uuid.UUID,
    rank: int,
    status: str = "initiated",
    vapi_call_id: Optional[str] = None,
) -> VapiCall:
    call = VapiCall(
        job_id=job_id,
        technician_id=tech_id,
        rank=rank,
        vapi_call_id=vapi_call_id,
        status=status,
    )
    session.add(call)
    session.commit()
    session.refresh(call)
    return call


def _update_call(
    session: Session,
    db_call: VapiCall,
    status: str,
    summary: str = "",
    transcript: str = "",
    agreed_price: Optional[float] = None,
) -> None:
    db_call.status = status
    db_call.call_summary = summary[:2000] if summary else None
    db_call.raw_transcript = transcript[:5000] if transcript else None
    db_call.agreed_price = agreed_price
    db_call.updated_at = datetime.now(timezone.utc)
    session.add(db_call)
    session.commit()


def _parse_outcome(vapi_call_data: Dict[str, Any]) -> str:
    """
    Determine outcome from a Vapi GET /call/{id} response.
    Returns: accepted | rejected | no_answer | pending | failed | in_progress
    """
    status = vapi_call_data.get("status", "")
    ended_reason = vapi_call_data.get("endedReason", "") or ""

    # Still active
    if status in ("queued", "ringing", "in-progress"):
        return "in_progress"

    # Did not connect at all
    if ended_reason in ("customer-did-not-answer", "no-answer", "voicemail", "busy"):
        return "no_answer"
    if ended_reason in ("error", "pipeline-error", "assistant-error", "call.start.error-get-transport"):
        return "failed"

    # Read all text sources
    summary    = vapi_call_data.get("summary", "") or ""
    artifact   = vapi_call_data.get("artifact", {}) or {}
    transcript = artifact.get("transcript", "") or ""
    messages   = artifact.get("messages", []) or []

    # Combine all assistant messages from the conversation
    assistant_text = " ".join(
        m.get("content", "") or m.get("message", "")
        for m in messages
        if m.get("role") in ("assistant", "bot")
    )
    full_text = (summary + " " + transcript + " " + assistant_text).lower()

    # --- Explicit outcome markers the AI is instructed to say ---
    if "outcome: accepted" in full_text or "outcome:accepted" in full_text:
        return "accepted"
    if "outcome: rejected" in full_text or "outcome:rejected" in full_text:
        return "rejected"
    if "outcome: pending" in full_text or "outcome:pending" in full_text:
        return "pending"

    # --- Broad acceptance keywords (real-world conversational responses) ---
    accept_kw = [
        "i accept", "i'll do it", "i will do it", "i'm in", "i am in",
        "sounds good", "that works", "that's fine", "that is fine",
        "yes i will", "yes i'll", "okay sure", "ok sure", "sure i'll",
        "agreed", "deal", "confirmed", "i agree", "let's do it", "let us do it",
        "count me in", "i can do it", "i can take", "i'll take it", "i will take it",
        "happy to help", "i'm available", "i am available", "no problem",
        "absolutely", "definitely", "for sure", "yes absolutely",
        "great i'll", "great i will", "perfect i'll", "yes that's fine",
    ]

    # --- Broad rejection keywords ---
    reject_kw = [
        "i decline", "i reject", "not interested", "no thank you", "no thanks",
        "can't do it", "cannot do it", "i can't", "i cannot",
        "not available", "won't be able", "unable to", "i'm not available",
        "sorry i", "i don't think", "i do not think", "pass on this",
        "not for me", "too low", "too less", "not enough", "won't work for me",
    ]

    # --- Pending keywords ---
    pending_kw = [
        "think about it", "call me back", "let me check", "get back to you",
        "let me think", "i'll consider", "i will consider", "need some time",
        "can i have", "give me time",
    ]

    for kw in accept_kw:
        if kw in full_text:
            logger.info(f"[Outcome] Matched accept keyword: '{kw}'")
            return "accepted"
    for kw in reject_kw:
        if kw in full_text:
            logger.info(f"[Outcome] Matched reject keyword: '{kw}'")
            return "rejected"
    for kw in pending_kw:
        if kw in full_text:
            return "pending"

    # Unknown end — if ended normally, treat as rejected to keep the chain moving
    if status == "ended":
        logger.warning(f"[Outcome] Call ended with no clear outcome, treating as rejected. Summary: {summary[:200]}")
        return "rejected"

    return "in_progress"


def _parse_agreed_price(vapi_call_data: Dict[str, Any]) -> Optional[float]:
    """Extract agreed price from summary/transcript."""
    summary = vapi_call_data.get("summary", "") or ""
    artifact = vapi_call_data.get("artifact", {}) or {}
    transcript = artifact.get("transcript", "") or ""
    text = summary + " " + transcript

    # Look for "AGREED_PRICE: 500"
    m = re.search(r"agreed_price[:\s]+(\d+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Generic patterns
    patterns = [
        r"agreed\s+(?:on|to|at)\s+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"confirmed\s+(?:at|for)\s+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)",
        r"\$([\d,]+(?:\.\d{1,2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


# ── Background Polling Worker ─────────────────────────────────────────────────

def _poll_and_progress(
    job_id: str,
    ranked: List[Dict[str, Any]],
    already_called: List[str],
    vapi_call_id: str,
    db_call_id: str,
    tech_id: str,
    poll_interval: int = 8,
    max_wait: int = 300,
) -> None:
    """
    Background thread: polls Vapi until the current call ends,
    then processes outcome and triggers next call if needed.
    No webhooks required.
    """
    logger.info(f"[Poll] Starting poll for vapi_call={vapi_call_id} tech={tech_id}")
    waited = 0

    # Own DB session for this background thread
    with Session(engine) as session:
        db_call = session.get(VapiCall, uuid.UUID(db_call_id))
        if not db_call:
            logger.error(f"[Poll] VapiCall {db_call_id} not found")
            return

        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval

            try:
                call_data = vapi_service.get_call_status(vapi_call_id)
            except Exception as exc:
                logger.warning(f"[Poll] get_call_status error: {exc}")
                continue

            outcome = _parse_outcome(call_data)

            if outcome == "in_progress":
                # Update status to in_progress if not already
                if db_call.status == "initiated":
                    db_call.status = "in_progress"
                    db_call.updated_at = datetime.now(timezone.utc)
                    session.add(db_call)
                    session.commit()
                logger.debug(f"[Poll] Call {vapi_call_id} still in progress ({waited}s)")
                continue

            # Call ended — process outcome
            summary = call_data.get("summary", "") or ""
            artifact = call_data.get("artifact", {}) or {}
            transcript = artifact.get("transcript", "") or ""
            agreed_price = _parse_agreed_price(call_data)

            # Fallback to tech's base rate if they accepted but we failed to parse a number
            if outcome == "accepted" and agreed_price is None:
                for item in ranked:
                    if str(item.get("technician_id") or item.get("id", "")) == tech_id:
                        agreed_price = float(item.get("base_hourly_rate") or 0.0)
                        logger.info(f"[Poll] Using fallback tech_rate for agreed_price: {agreed_price}")
                        break

            _update_call(session, db_call, outcome, summary, transcript, agreed_price)
            logger.info(f"[Poll] Call {vapi_call_id} ended: outcome={outcome} price={agreed_price}")

            job = session.get(Job, uuid.UUID(job_id))
            if not job:
                logger.error(f"[Poll] Job {job_id} not found")
                return

            if outcome == "accepted":
                # ✅ Auto-assign the technician
                try:
                    job_service.assign_technician(
                        session, job.id, uuid.UUID(tech_id), job.customer_id
                    )
                    if agreed_price:
                        job.final_price = agreed_price
                        job.proposed_price = agreed_price
                        session.add(job)
                        session.commit()
                    logger.info(f"[Poll] SUCCESS — tech {tech_id} assigned to job {job_id} @ {agreed_price}")
                    
                    # 🎉 Send WhatsApp Notification to Technician
                    tech = _get_technician_by_id(session, tech_id)
                    customer = session.get(User, job.customer_id)
                    if tech and tech.phone:
                        company_name = customer.full_name or "VERO Platform Client" if customer else "VERO Platform"
                        twilio_service.send_whatsapp_assignment_notification(
                            tech_phone=tech.phone,
                            tech_name=tech.full_name or "Technician",
                            job_title=job.title,
                            job_description=job.description or "",
                            company_name=company_name,
                            agreed_price=agreed_price or 0.0,
                        )

                except Exception as exc:
                    logger.error(f"[Poll] Assignment failed: {exc}")
            else:
                # ❌ Try the next technician in rank order
                logger.info(f"[Poll] outcome={outcome} — calling next technician")
                _call_next_ranked(session, job, ranked, already_called)
            return

        # Timed out — mark as no_answer
        logger.warning(f"[Poll] Call {vapi_call_id} timed out after {max_wait}s")
        _update_call(session, db_call, "no_answer")
        job = session.get(Job, uuid.UUID(job_id))
        if job:
            _call_next_ranked(session, job, ranked, already_called)


def _call_next_ranked(
    session: Session,
    job: Job,
    ranked: List[Dict[str, Any]],
    already_called: List[str],
) -> None:
    """Place a call to the next uncalled technician in rank order."""
    for item in ranked:
        tech_id = item.get("technician_id") or item.get("id", "")
        if tech_id in already_called:
            continue

        tech = _get_technician_by_id(session, tech_id)
        if not tech or not tech.phone:
            reason = "not found" if not tech else "no phone"
            logger.warning(f"[Poll] Skipping tech {tech_id}: {reason}")
            _record_call(session, job.id,
                         uuid.UUID(tech_id) if tech else uuid.UUID("00000000-0000-0000-0000-000000000000"),
                         len(already_called) + 1, status="failed")
            already_called.append(tech_id)
            continue

        tech_rate = float(item.get("base_hourly_rate") or tech.base_hourly_rate or tech.price or 0.0)
        job_budget = float(job.budget or 0.0)
        rank = len(already_called) + 1
        new_already_called = already_called + [tech_id]

        try:
            vapi_response = vapi_service.place_call(
                phone_number=tech.phone,
                tech_name=tech.full_name or "Technician",
                job_title=job.title,
                job_description=job.description or "",
                required_skills=job.required_skills or [],
                job_budget=job_budget,
                tech_rate=tech_rate,
                webhook_url="",  # Not needed — we use polling
                metadata={
                    "job_id": str(job.id),
                    "technician_id": str(tech.id),
                    "rank": rank,
                },
            )
            vapi_call_id = vapi_response.get("id")
            db_call = _record_call(
                session, job.id, tech.id, rank,
                status="initiated", vapi_call_id=vapi_call_id,
            )
            logger.info(f"[Poll] Call #{rank} placed → tech={tech_id}, vapi_id={vapi_call_id}")

            # Start background polling thread for this call
            t = threading.Thread(
                target=_poll_and_progress,
                args=(str(job.id), ranked, new_already_called, vapi_call_id, str(db_call.id), str(tech.id)),
                daemon=True,
            )
            t.start()
            return

        except Exception as exc:
            logger.error(f"[Poll] Vapi call failed for tech {tech_id}: {exc}")
            _record_call(session, job.id, tech.id, rank, status="failed")
            already_called.append(tech_id)
            continue

    logger.warning(f"[Poll] Campaign exhausted — no more technicians for job {job.id}")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/{job_id}")
def trigger_auto_assign(
    job_id: uuid.UUID,
    body: AutoAssignRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """
    Start the AI auto-calling campaign.
    Works entirely via polling — no webhooks or public URL required.
    """
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your job")

    if not body.technicians:
        raise HTTPException(status_code=400, detail="No ranked technicians provided")

    # Prevent duplicate campaign
    existing = session.exec(
        select(VapiCall)
        .where(VapiCall.job_id == job_id)
        .where(VapiCall.status.in_(["initiated", "in_progress"]))
    ).all()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A calling campaign is already running for this job"
        )

    ranked = body.technicians

    # Find the first callable technician and kick off the polling chain
    for item in ranked:
        tech_id = item.get("technician_id") or item.get("id", "")
        tech = _get_technician_by_id(session, tech_id)
        if not tech or not tech.phone:
            continue

        tech_rate = float(item.get("base_hourly_rate") or tech.base_hourly_rate or tech.price or 0.0)
        job_budget = float(job.budget or 0.0)
        rank = ranked.index(item) + 1
        already_called = [tech_id]

        try:
            vapi_response = vapi_service.place_call(
                phone_number=tech.phone,
                tech_name=tech.full_name or "Technician",
                job_title=job.title,
                job_description=job.description or "",
                required_skills=job.required_skills or [],
                job_budget=job_budget,
                tech_rate=tech_rate,
                webhook_url="",  # polling mode — no webhook needed
                metadata={"job_id": str(job.id), "technician_id": str(tech.id), "rank": rank},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Vapi call failed: {exc}")

        vapi_call_id = vapi_response.get("id")
        db_call = _record_call(session, job.id, tech.id, rank, status="initiated", vapi_call_id=vapi_call_id)

        # Start background polling thread — auto-chains to next technician on rejection
        t = threading.Thread(
            target=_poll_and_progress,
            args=(str(job.id), ranked, already_called, vapi_call_id, str(db_call.id), str(tech.id)),
            daemon=True,
        )
        t.start()

        return {
            "message": "Auto-assign campaign started (polling mode — no webhook needed)",
            "job_id": str(job_id),
            "first_call_rank": rank,
            "vapi_call_id": vapi_call_id,
            "technician": tech.full_name,
        }

    raise HTTPException(
        status_code=422,
        detail="No reachable technicians (all missing phone numbers?)"
    )


@router.get("/{job_id}/status", response_model=CallStatusResponse)
def get_campaign_status(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    """Poll the status of the auto-assign calling campaign."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    calls = session.exec(
        select(VapiCall).where(VapiCall.job_id == job_id).order_by(VapiCall.rank)
    ).all()

    calls_data = [
        {
            "rank": c.rank,
            "technician_id": str(c.technician_id),
            "vapi_call_id": c.vapi_call_id,
            "status": c.status,
            "agreed_price": c.agreed_price,
            "call_summary": c.call_summary,
            "created_at": c.created_at.isoformat(),
        }
        for c in calls
    ]

    statuses = [c.status for c in calls]
    if any(s == "accepted" for s in statuses):
        overall = "completed"
    elif any(s in ("initiated", "in_progress") for s in statuses):
        overall = "calling"
    elif calls and all(s in ("rejected", "no_answer", "failed", "pending") for s in statuses):
        overall = "exhausted"
    else:
        overall = "idle"

    accepted_call = next((c for c in calls if c.status == "accepted"), None)

    return CallStatusResponse(
        job_id=str(job_id),
        status=overall,
        calls=calls_data,
        assigned_technician_id=str(accepted_call.technician_id) if accepted_call else None,
    )


# ── Optional: Vapi webhook (kept for production use with ngrok) ───────────────

@router.post("/webhook/vapi")
async def vapi_webhook(request: Request, session: Session = Depends(get_session)):
    """
    Optional webhook endpoint. Only needed if you want Vapi to push events
    instead of polling. Works in production with a public URL.
    For local dev, polling mode above is used instead.
    """
    secret = request.headers.get("x-vapi-secret", "")
    expected = getattr(settings, "VAPI_WEBHOOK_SECRET", "") or ""
    if expected and expected != "your_webhook_secret_here" and secret != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    payload: Dict[str, Any] = await request.json()
    logger.info(f"Vapi webhook received (type={payload.get('type') or payload.get('message', {}).get('type')})")
    return {"status": "ok", "note": "polling mode active — webhook ignored"}
