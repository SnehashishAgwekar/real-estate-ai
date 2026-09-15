# ============================================================
# new_sender.py
# ============================================================
# Handles:
#
#   SMS       -> TextBee
#   WhatsApp  -> WaSender
#   Email     -> Resend
#
# ============================================================
import logging
import os
import re
import requests
import resend
from dotenv import load_dotenv

from app.core.template import (
    broker_interest_sms,
    broker_interest_whatsapp,
    broker_property_whatsapp,
    broker_interest_email,
)

logger = logging.getLogger("estateagent.sender")

# ============================================================
# LOAD .ENV
# ============================================================
load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================
TEXTBEE_API_URL = "https://api.textbee.dev/api/v1/gateway/send-bulk-sms"
TEXTBEE_DEVICE_ID = os.getenv("TEXTBEE_DEVICE_ID", "6aa25227ccb6c72709ca8558")
WASENDER_API_URL = "https://www.wasenderapi.com/api/send-message"
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
DEFAULT_COUNTRY_CODE = os.getenv("SMS_DEFAULT_COUNTRY_CODE", "+91")


def normalize_phone(raw: str | None) -> str | None:
    """Best-effort E.164 phone formatting."""
    if not raw:
        return None
    s = re.sub(r"[^\d+]", "", raw.strip())
    if not s:
        return None
    if s.startswith("+"):
        return s
    if s.startswith("00"):
        return "+" + s[2:]
    if len(s) == 10:
        return f"{DEFAULT_COUNTRY_CODE}{s}"
    if s.startswith("91") and len(s) == 12:
        return f"+{s}"
    return f"+{s}"


# ============================================================
# ENVIRONMENT VARIABLE HELPER
# ============================================================
def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is not set in the .env file.")
    return value


# ============================================================
# SMS
# ============================================================
def send_sms(
    phone: str,
    user_name: str,
    property_name: str,
    user_phone: str,
):
    api_key = get_env("TEXTBEE_API_KEY")
    target_phone = normalize_phone(phone) or phone
    message = broker_interest_sms(
        user_name=user_name,
        property_name=property_name,
        user_phone=user_phone,
    )
    device_id = os.getenv("TEXTBEE_DEVICE_ID", TEXTBEE_DEVICE_ID)
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "deviceId": device_id,
        "messages": [
            {
                "recipients": [target_phone],
                "message": message,
            }
        ],
    }
    response = requests.post(
        TEXTBEE_API_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ============================================================
# WHATSAPP - GENERIC
# ============================================================
def send_whatsapp(
    phone: str,
    message: str,
):
    api_key = get_env("WASENDER_API_KEY")
    target_phone = normalize_phone(phone) or phone
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": target_phone,
        "text": message,
    }
    response = requests.post(
        WASENDER_API_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ============================================================
# WHATSAPP - PROPERTY ALERT
# ============================================================
def send_property_whatsapp(
    phone: str,
    property_name: str,
    location: str,
    price: str,
    area: str,
):
    message = broker_property_whatsapp(
        property_name=property_name,
        location=location,
        price=price,
        area=area,
    )
    return send_whatsapp(
        phone=phone,
        message=message,
    )


# ============================================================
# WHATSAPP - BROKER NOTIFICATION
# ============================================================
def send_broker_whatsapp(
    phone: str,
    user_name: str,
    property_name: str,
    user_phone: str,
):
    message = broker_interest_whatsapp(
        user_name=user_name,
        property_name=property_name,
        user_phone=user_phone,
    )
    return send_whatsapp(
        phone=phone,
        message=message,
    )


# ============================================================
# EMAIL
# ============================================================
def send_email(
    email: str,
    user_name: str,
    property_name: str,
    user_phone: str,
):
    api_key = get_env("RESEND_API_KEY")
    resend.api_key = api_key
    from_email = os.getenv("RESEND_FROM_EMAIL", RESEND_FROM_EMAIL)
    html_message = broker_interest_email(
        user_name=user_name,
        property_name=property_name,
        user_phone=user_phone,
    )
    response = resend.Emails.send(
        {
            "from": from_email,
            "to": [email],
            "subject": f"New Property Interest - {property_name}",
            "html": html_message,
        }
    )
    return response


# ============================================================
# NOTIFY BROKER
# ============================================================
def notify_broker(
    broker_phone: str | None,
    broker_email: str | None,
    user_name: str | None = None,
    property_name: str = "Property",
    user_phone: str | None = None,
    user_email: str | None = None,
):
    result = {
        "sms": None,
        "whatsapp": None,
        "email": None,
    }

    display_user_name = (user_name or "").strip() or "Interested Customer"
    contact_parts = []
    if user_phone and str(user_phone).strip():
        contact_parts.append(str(user_phone).strip())
    if user_email and str(user_email).strip() and (not user_phone or str(user_email).strip() not in str(user_phone)):
        contact_parts.append(str(user_email).strip())
    display_contact = " / ".join(contact_parts) if contact_parts else "Not provided"
    target_property_name = property_name or "Property"

    # --------------------------------------------------------
    # SMS (TextBee)
    # --------------------------------------------------------
    if broker_phone and str(broker_phone).strip():
        try:
            sms_resp = send_sms(
                phone=str(broker_phone).strip(),
                user_name=display_user_name,
                property_name=target_property_name,
                user_phone=display_contact,
            )
            result["sms"] = {
                "success": True,
                "response": sms_resp,
            }
            logger.info("SMS delivered to broker %s for %s", broker_phone, target_property_name)
        except Exception as e:
            logger.error("SMS notification to %s failed: %s", broker_phone, e)
            result["sms"] = {
                "success": False,
                "error": str(e),
            }
    else:
        result["sms"] = {
            "success": False,
            "skipped": True,
            "reason": "Broker phone not provided",
        }

    # --------------------------------------------------------
    # WHATSAPP (WaSender)
    # --------------------------------------------------------
    if broker_phone and str(broker_phone).strip():
        try:
            wa_resp = send_broker_whatsapp(
                phone=str(broker_phone).strip(),
                user_name=display_user_name,
                property_name=target_property_name,
                user_phone=display_contact,
            )
            result["whatsapp"] = {
                "success": True,
                "response": wa_resp,
            }
            logger.info("WhatsApp delivered to broker %s for %s", broker_phone, target_property_name)
        except Exception as e:
            logger.error("WhatsApp notification to %s failed: %s", broker_phone, e)
            result["whatsapp"] = {
                "success": False,
                "error": str(e),
            }
    else:
        result["whatsapp"] = {
            "success": False,
            "skipped": True,
            "reason": "Broker phone not provided",
        }

    # --------------------------------------------------------
    # EMAIL (Resend)
    # --------------------------------------------------------
    if broker_email and str(broker_email).strip():
        try:
            email_resp = send_email(
                email=str(broker_email).strip(),
                user_name=display_user_name,
                property_name=target_property_name,
                user_phone=display_contact,
            )
            result["email"] = {
                "success": True,
                "response": email_resp,
            }
            logger.info("Email delivered to broker %s for %s", broker_email, target_property_name)
        except Exception as e:
            logger.error("Email notification to %s failed: %s", broker_email, e)
            result["email"] = {
                "success": False,
                "error": str(e),
            }
    else:
        result["email"] = {
            "success": False,
            "skipped": True,
            "reason": "Broker email not provided",
        }

    return result
