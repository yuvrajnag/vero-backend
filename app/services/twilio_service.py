"""
Twilio WhatsApp Service
-----------------------
Sends WhatsApp notifications to technicians.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.utils.logger import logger
from app.services.vapi_service import _normalize_phone

def send_whatsapp_assignment_notification(
    tech_phone: str,
    tech_name: str,
    job_title: str,
    job_description: str,
    company_name: str,
    agreed_price: float,
) -> bool:
    """
    Sends a WhatsApp message to the technician via Twilio Programmable Messaging API.
    Returns True if successful, False otherwise.
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
    from_number = getattr(settings, "TWILIO_WHATSAPP_NUMBER", None)

    if not all([account_sid, auth_token, from_number]):
        logger.warning("Twilio WhatsApp config missing. Skipping notification.")
        return False

    # Check for test override
    test_override = getattr(settings, "TEST_PHONE_OVERRIDE", None)
    if test_override:
        logger.warning(f"[TEST MODE] WhatsApp overriding phone {tech_phone} → {test_override}")
        target_phone = test_override
    else:
        target_phone = tech_phone

    target_e164 = _normalize_phone(target_phone)
    # Twilio requires "whatsapp:" prefix for WhatsApp numbers
    to_whatsapp = f"whatsapp:{target_e164}"

    # Format the message
    price_str = f"Rs. {agreed_price:.2f}" if agreed_price else "the agreed rate"
    message_body = (
        f"Hi {tech_name}, congratulations! 🎉\n\n"
        f"You have been successfully assigned to the job: *{job_title}*.\n\n"
        f"*Company:* {company_name}\n"
        f"*Agreed Rate:* {price_str} / day\n\n"
        f"Job Details: {job_description}\n\n"
        f"The VERO Platform team will reach out with next steps soon. See you!"
    )

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    
    data = {
        "From": from_number,
        "To": to_whatsapp,
        "Body": message_body,
    }

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(
                url,
                data=data,
                auth=(account_sid, auth_token),
            )
            response.raise_for_status()
            logger.info(f"WhatsApp notification sent successfully to {to_whatsapp}")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send WhatsApp message: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {str(e)}")
        return False
