"""Operator notifications for Big Beautiful Screens.

Sends email to the operator through Resend's REST API when notable things
happen (currently: new user signups). Does nothing unless RESEND_API_KEY and
SIGNUP_NOTIFY_EMAIL are configured.
"""

import httpx

from .config import get_settings

RESEND_API_URL = "https://api.resend.com/emails"


async def send_signup_notification(email: str, name: str | None, user_id: str) -> None:
    """Email the operator about a new user signup.

    Raises httpx.HTTPError if Resend rejects the request; callers should
    catch it so a failed email never blocks the signup itself.
    """
    settings = get_settings()
    if not settings.RESEND_API_KEY or not settings.SIGNUP_NOTIFY_EMAIL:
        return

    display = f"{name} <{email}>" if name else email
    text = "\n".join(
        [
            f"New signup on {settings.APP_URL}",
            "",
            f"User: {display}",
            f"User ID: {user_id}",
        ]
    )

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": settings.SIGNUP_NOTIFY_FROM,
                "to": [settings.SIGNUP_NOTIFY_EMAIL],
                "subject": f"New signup: {email}",
                "text": text,
            },
        )
        response.raise_for_status()
