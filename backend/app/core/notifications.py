"""
Outbound SMS notifications.

Provider-agnostic: set SMS_PROVIDER (+ that provider's credentials) in .env to
turn real sending on. Until then every call just logs the message and returns
False, so the rest of the app keeps working with no SMS account.

Supported values for SMS_PROVIDER:
  - "twilio"    -> needs TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
  - "msg91"     -> not implemented yet (raises); stub kept for wiring
  - "fast2sms"  -> not implemented yet (raises); stub kept for wiring
  - unset/other -> log only (dormant)
"""
import logging
import os
import re

import requests

logger = logging.getLogger("estateagent.sms")

SMS_PROVIDER = (os.getenv("SMS_PROVIDER") or "").strip().lower()
DEFAULT_COUNTRY_CODE = os.getenv("SMS_DEFAULT_COUNTRY_CODE", "+91")


def normalize_phone(raw: str | None) -> str | None:
    """Best-effort E.164. Bare 10-digit numbers get DEFAULT_COUNTRY_CODE."""
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


def _send_twilio(to: str, body: str) -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    sender = os.getenv("TWILIO_FROM_NUMBER")
    if not (sid and token and sender):
        logger.warning("SMS_PROVIDER=twilio but TWILIO_* env vars are incomplete; skipping send")
        return False
    resp = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        auth=(sid, token),
        data={"From": sender, "To": to, "Body": body},
        timeout=10,
    )
    if resp.status_code >= 300:
        logger.error("Twilio send failed (%s): %s", resp.status_code, resp.text[:300])
        return False
    return True


def _send_not_implemented(provider: str):
    def _inner(to: str, body: str) -> bool:  # noqa: ARG001
        raise NotImplementedError(
            f"SMS_PROVIDER={provider!r} is not implemented yet. "
            "Implement app.core.notifications._send_" + provider
        )
    return _inner


_PROVIDERS = {
    "twilio": _send_twilio,
    "msg91": _send_not_implemented("msg91"),
    "fast2sms": _send_not_implemented("fast2sms"),
}


def send_sms(to: str | None, body: str) -> bool:
    """
    Send one SMS. Returns True only if a provider actually accepted it.
    Never raises for normal failures (missing creds, bad number, provider error)
    so callers can fire-and-forget.
    """
    number = normalize_phone(to)
    if not number:
        logger.info("[SMS skipped: no phone] %s", body)
        return False

    sender = _PROVIDERS.get(SMS_PROVIDER)
    if sender is None:
        # Dormant mode: no provider configured. Log so it's visible in dev.
        logger.info("[SMS -> %s] %s", number, body)
        return False

    try:
        ok = sender(number, body)
        if ok:
            logger.info("SMS delivered to %s via %s", number, SMS_PROVIDER)
        return ok
    except Exception as exc:  # noqa: BLE001 - notifications must never break the request
        logger.error("SMS to %s via %s errored: %s", number, SMS_PROVIDER, exc)
        return False


def notify_property_interest(
    *,
    property_name: str,
    buyer_name: str | None,
    buyer_phone: str | None,
    buyer_email: str | None,
    broker_name: str | None,
    broker_phone: str | None,
    broker_email: str | None,
) -> None:
    """Text both sides after a user taps Interested. Safe to run in the background."""
    buyer_label = buyer_name or "A buyer"
    broker_label = broker_name or "the broker"

    send_sms(
        broker_phone,
        f"EstateAgent AI: {buyer_label} is interested in your listing "
        f"\"{property_name}\". Contact them at "
        f"{buyer_phone or 'N/A'}"
        + (f" / {buyer_email}" if buyer_email else "")
        + ".",
    )
    send_sms(
        buyer_phone,
        f"EstateAgent AI: Your interest in \"{property_name}\" was sent to "
        f"{broker_label}. You can contact the broker directly at "
        f"{broker_phone or 'N/A'}"
        + (f" / {broker_email}" if broker_email else "")
        + ".",
    )
