"""WhatsApp notifications via Twilio's WhatsApp API.

Requires a Twilio account with WhatsApp enabled - either the free
Sandbox (twilio.com/docs/whatsapp/sandbox) for testing, or an approved
WhatsApp Business sender for production use. Needs four things, all
optional (this whole feature is a no-op until every one is set):

    TWILIO_SID     - Account SID from the Twilio Console
    TWILIO_TOKEN   - Auth Token from the Twilio Console
    TWILIO_PHONE   - Twilio's WhatsApp-enabled sender number
    WHATSAPP_TO    - your own WhatsApp number, to receive alerts

If you're using the Sandbox, TWILIO_PHONE is the shared sandbox number
shown on that page, and your own WHATSAPP_TO number must first send
the sandbox's "join <code>" message on WhatsApp before Twilio will
deliver anything to it - this only needs to be done once, but expires
after a few months of inactivity and would need re-joining.
"""

import asyncio

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.config.settings import settings


def _is_configured() -> bool:

    return bool(
        settings.twilio_sid
        and settings.twilio_token
        and settings.twilio_phone
        and settings.whatsapp_to
    )


def _as_whatsapp_number(number: str) -> str:

    number = number.strip()
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


def _send_sync(text: str) -> bool:
    """Blocking Twilio API call. Never call this directly from async
    code - see send_whatsapp() below, which offloads it to a worker
    thread the same way fast_flights' blocking get_flights() call is
    handled, to avoid freezing the bot's Telegram long-poll
    connection."""

    if not _is_configured():
        return False

    try:
        client = Client(settings.twilio_sid, settings.twilio_token)

        client.messages.create(
            from_=_as_whatsapp_number(settings.twilio_phone),
            to=_as_whatsapp_number(settings.whatsapp_to),
            body=text,
        )
        return True

    except TwilioRestException as exc:

        print(f"WhatsApp (Twilio) send failed: {exc}")
        return False


async def send_whatsapp(text: str) -> bool:
    """Send a WhatsApp message with the given text. Returns True on
    success, False if not configured or if the send failed (never
    raises - a WhatsApp delivery problem shouldn't stop the bot's
    other notification channels or crash the scheduler)."""

    if not _is_configured():
        return False

    return await asyncio.to_thread(_send_sync, text)
