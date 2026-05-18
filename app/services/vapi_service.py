"""
Vapi Auto-Call Service
-----------------------
Triggers outbound AI phone calls to technicians via Vapi using a Twilio number.
The AI agent negotiates the job price with the technician on behalf of the company.

Vapi API docs: https://docs.vapi.ai/api-reference/calls/create

SETUP:
  In your .env set:
    VAPI_API_KEY=<from app.vapi.ai → Settings → API Keys>
    VAPI_ASSISTANT_ID=<optional: pre-built assistant ID from Vapi dashboard>
    VAPI_PHONE_NUMBER_ID=<the UUID shown in Vapi dashboard → Phone Numbers>
    PUBLIC_BASE_URL=<your backend's public URL — Vapi needs to reach this>

  If you don't have a pre-built assistant, leave VAPI_ASSISTANT_ID blank and
  the service will send an inline assistant definition on every call.

  NOTE: VAPI_PHONE_NUMBER_ID must be the UUID (e.g. ph_xxxxxxxx) shown in
  the Vapi dashboard, NOT the raw Twilio/E.164 number like +1-xxx-xxx-xxxx.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.utils.logger import logger

VAPI_BASE_URL = "https://api.vapi.ai"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.VAPI_API_KEY}",
        "Content-Type": "application/json",
    }


def _normalize_phone(phone: str) -> str:
    """Strip spaces/dashes/parens and ensure E.164 format (+countrycode...)."""
    digits = re.sub(r"[^\d+]", "", phone)
    if not digits.startswith("+"):
        # Assume Indian number if no country code and 10 digits
        if len(digits) == 10:
            digits = "+91" + digits
        else:
            digits = "+" + digits
    return digits


def build_negotiation_prompt(
    tech_name: str,
    job_title: str,
    job_description: str,
    required_skills: List[str],
    job_budget: float,
    tech_rate: float,
    company_name: str = "VERO Platform",
) -> str:
    """Build the system prompt for the AI negotiation agent."""
    skills_str = ", ".join(required_skills) if required_skills else "general technical work"
    return f"""You are an AI hiring coordinator for {company_name}, a professional workforce platform.
You are calling {tech_name}, a skilled technician, about a new job opportunity.

JOB DETAILS:
- Job Title: {job_title}
- Description: {job_description}
- Required Skills: {skills_str}
- Client Budget: {job_budget:.2f} per day
- Technician Listed Rate: {tech_rate:.2f} per day

YOUR STEP-BY-STEP GOAL:
1. Greet the technician by name and briefly introduce yourself as calling from VERO, a professional workforce platform.
2. Describe the job opportunity clearly and ask if they are available and interested.
3. Discuss the rate:
   - If their rate is at or below the client budget, confirm the engagement at their rate.
   - If their rate is above the budget, politely negotiate and explain the client's budget constraint.
   - You may go up to 10% above the budget to close the deal if they resist.
4. If they agree to a price, explicitly confirm: "Great, so we have agreed on [price] per day. I will send you a confirmation shortly."
5. If they decline or are unavailable, thank them warmly and end the call.

IMPORTANT RULES:
- Keep the call professional, friendly, and under 3 minutes.
- Never reveal who the client is — only say "one of our clients".
- If the technician needs time to think, politely note this as pending and end the call.
- At the very end of the call, always state: OUTCOME: accepted / rejected / pending, AGREED_PRICE: [amount or none].
"""


# ── Call Placement ────────────────────────────────────────────────────────────

def place_call(
    phone_number: str,
    tech_name: str,
    job_title: str,
    job_description: str,
    required_skills: List[str],
    job_budget: float,
    tech_rate: float,
    webhook_url: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Place an outbound call via Vapi.

    Matches Vapi's sample format:
        POST https://api.vapi.ai/call
        {
            "assistantId": "...",   ← if VAPI_ASSISTANT_ID is set
            OR
            "assistant": {...},     ← inline definition (no assistant ID needed)
            "phoneNumberId": "...", ← UUID from Vapi dashboard
            "customer": {
                "number": "+91XXXXXXXXXX",
                "name": "Technician Name"
            },
            "metadata": {...}
        }

    Returns the Vapi API response dict. Raises httpx.HTTPStatusError on failure.
    """
    # Normalise phone number to E.164 format
    test_override = getattr(settings, "TEST_PHONE_OVERRIDE", None)
    if test_override:
        logger.warning(f"[TEST MODE] Overriding phone {phone_number} → {test_override}")
        e164_phone = _normalize_phone(test_override)
    else:
        e164_phone = _normalize_phone(phone_number)

    # ── Build the payload ──────────────────────────────────────────────────
    payload: Dict[str, Any] = {}

    # Use pre-built assistant if configured, otherwise send inline definition
    assistant_id = getattr(settings, "VAPI_ASSISTANT_ID", None)
    if assistant_id:
        payload["assistantId"] = assistant_id
        # Pass job context via assistantOverrides so the pre-built assistant
        # picks up the dynamic negotiation prompt for this specific call
        payload["assistantOverrides"] = {
            "firstMessage": (
                f"Hello, may I speak with {tech_name}? "
                f"I'm calling from VERO Platform regarding a {job_title} opportunity."
            ),
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": build_negotiation_prompt(
                            tech_name=tech_name,
                            job_title=job_title,
                            job_description=job_description,
                            required_skills=required_skills,
                            job_budget=job_budget,
                            tech_rate=tech_rate,
                        ),
                    }
                ],
            },
        }
    else:
        # Fully inline assistant — no Vapi dashboard setup needed
        payload["assistant"] = {
            "name": "VERO Hiring Coordinator",
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": build_negotiation_prompt(
                            tech_name=tech_name,
                            job_title=job_title,
                            job_description=job_description,
                            required_skills=required_skills,
                            job_budget=job_budget,
                            tech_rate=tech_rate,
                        ),
                    }
                ],
                "temperature": 0.7,
                "maxTokens": 512,
            },
            # Matches dashboard: Sarah / 11labs / eleven_turbo_v2_5
            "voice": {
                "provider": "11labs",
                "voiceId": "sarah",
                "model": "eleven_turbo_v2_5",
            },
            "firstMessage": (
                f"Hello, may I speak with {tech_name}? "
                f"I'm calling from VERO Platform regarding a {job_title} opportunity."
            ),
            "endCallMessage": "Thank you for your time. Have a great day!",
            # Matches dashboard: Deepgram nova-3 multilingual
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-3",
                "language": "multi",
            },
            "serverUrl": webhook_url,
            "serverUrlSecret": getattr(settings, "VAPI_WEBHOOK_SECRET", None) or "",
            "endCallFunctionEnabled": True,
            "silenceTimeoutSeconds": 30,
            "maxDurationSeconds": 300,
        }

    # Phone number identifier (Vapi UUID, not the raw E.164 number)
    phone_number_id = getattr(settings, "VAPI_PHONE_NUMBER_ID", None)
    if phone_number_id:
        # If the user accidentally put the E.164 number here, Vapi will error;
        # we pass it as-is and let Vapi return a clear error message.
        payload["phoneNumberId"] = phone_number_id

    # Customer details
    payload["customer"] = {
        "number": e164_phone,
        "name": tech_name,
    }

    # Metadata — passed back to our webhook so we know which job/tech this is
    payload["metadata"] = metadata or {}

    logger.info(
        f"Vapi: placing call to {e164_phone} ({tech_name}) "
        f"for job '{job_title}' | budget={job_budget} | tech_rate={tech_rate}"
    )

    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{VAPI_BASE_URL}/call",
            headers=_headers(),
            json=payload,
        )
        # Log full error body for easier debugging
        if not response.is_success:
            logger.error(
                f"Vapi call failed: status={response.status_code} body={response.text}"
            )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Vapi call initiated: call_id={result.get('id')} → {e164_phone}")
        return result


def get_call_status(vapi_call_id: str) -> Dict[str, Any]:
    """Fetch current Vapi call status by call ID."""
    with httpx.Client(timeout=15) as client:
        response = client.get(
            f"{VAPI_BASE_URL}/call/{vapi_call_id}",
            headers=_headers(),
        )
        response.raise_for_status()
        return response.json()
