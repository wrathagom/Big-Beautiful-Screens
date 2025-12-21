"""Webhook handlers for Big Beautiful Screens.

Handles Clerk webhooks for user and organization sync.
"""

import hashlib
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request

from .config import AppMode, get_settings
from .db import get_database

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_clerk_signature(payload: bytes, signature: str, timestamp: str, secret: str) -> bool:
    """Verify Clerk webhook signature using Svix."""
    # Clerk uses Svix for webhooks
    # Signature format: v1,<signature>
    try:
        # Create the signed payload
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"

        # Parse the signature (format: v1,base64signature)
        parts = signature.split(",")
        signatures = []
        for part in parts:
            if part.startswith("v1,"):
                signatures.append(part[3:])
            elif "," not in part and len(parts) == 1:
                # Handle simple signature format
                signatures.append(part)

        if not signatures:
            return False

        # Compute expected signature
        import base64

        expected = hmac.new(
            secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).digest()
        expected_b64 = base64.b64encode(expected).decode("utf-8")

        # Check if any signature matches
        return any(hmac.compare_digest(expected_b64, sig) for sig in signatures)

    except Exception as e:
        print(f"Signature verification error: {e}")
        return False


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    svix_id: str | None = Header(default=None, alias="svix-id"),
    svix_timestamp: str | None = Header(default=None, alias="svix-timestamp"),
    svix_signature: str | None = Header(default=None, alias="svix-signature"),
):
    """Handle Clerk webhook events for user and organization sync.

    Events handled:
    - user.created: Create user in database
    - user.updated: Update user in database
    - user.deleted: Delete user from database
    - organization.created: Create organization in database
    - organization.updated: Update organization in database
    - organization.deleted: Delete organization from database
    - organizationMembership.created: Add user to organization
    - organizationMembership.deleted: Remove user from organization
    """
    settings = get_settings()

    # Only process in SaaS mode
    if settings.APP_MODE != AppMode.SAAS:
        raise HTTPException(status_code=404, detail="Not found")

    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature if secret is configured
    if settings.CLERK_WEBHOOK_SECRET:
        if not svix_id or not svix_timestamp or not svix_signature:
            raise HTTPException(status_code=400, detail="Missing webhook headers")

        if not _verify_clerk_signature(
            body, svix_signature, svix_timestamp, settings.CLERK_WEBHOOK_SECRET
        ):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse the event
    try:
        event = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    event_type = event.get("type")
    data = event.get("data", {})

    db = get_database()

    # Handle user events
    if event_type == "user.created" or event_type == "user.updated":
        user_id = data.get("id")
        email = None
        # Get primary email
        email_addresses = data.get("email_addresses", [])
        for addr in email_addresses:
            if addr.get("id") == data.get("primary_email_address_id"):
                email = addr.get("email_address")
                break
        if not email and email_addresses:
            email = email_addresses[0].get("email_address")

        name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or None

        if user_id and email:
            await db.create_or_update_user(
                user_id=user_id,
                email=email,
                name=name,
                plan="free",  # Default plan
            )

    elif event_type == "user.deleted":
        user_id = data.get("id")
        if user_id:
            await db.delete_user(user_id)

    # Handle organization events
    elif event_type == "organization.created" or event_type == "organization.updated":
        org_id = data.get("id")
        name = data.get("name")
        slug = data.get("slug")

        if org_id and name and slug:
            await db.create_or_update_organization(
                org_id=org_id,
                name=name,
                slug=slug,
                plan="free",  # Default plan
            )

    elif event_type == "organization.deleted":
        org_id = data.get("id")
        if org_id:
            await db.delete_organization(org_id)

    # Handle membership events
    elif event_type == "organizationMembership.created":
        org_membership = data.get("organization_membership", data)
        user_id = org_membership.get("public_user_data", {}).get("user_id")
        org_id = org_membership.get("organization", {}).get("id")
        role = org_membership.get("role", "member")

        if user_id and org_id:
            await db.add_org_member(user_id, org_id, role)

    elif event_type == "organizationMembership.deleted":
        org_membership = data.get("organization_membership", data)
        user_id = org_membership.get("public_user_data", {}).get("user_id")
        org_id = org_membership.get("organization", {}).get("id")

        if user_id and org_id:
            await db.remove_org_member(user_id, org_id)

    return {"success": True, "event": event_type}
