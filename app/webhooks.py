"""Webhook handlers for Big Beautiful Screens.

Handles Clerk webhooks for user and organization sync.
Handles Stripe webhooks for subscription management.
"""

import json

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from svix.webhooks import Webhook, WebhookVerificationError

from .config import AppMode, get_settings
from .db import get_database

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


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

        try:
            wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
            event = wh.verify(
                body,
                {
                    "svix-id": svix_id,
                    "svix-timestamp": svix_timestamp,
                    "svix-signature": svix_signature,
                },
            )
        except WebhookVerificationError as e:
            print(f"Clerk webhook verification failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid signature") from e
    else:
        # No secret configured, just parse the JSON
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
            # Check if user is new to OUR database (not just Clerk)
            # This handles the case where DB is reset but user exists in Clerk
            existing_user = await db.get_user(user_id)
            is_new_user = existing_user is None

            await db.create_or_update_user(
                user_id=user_id,
                email=email,
                name=name,
                plan="free",  # Default plan
            )

            # Create demo screen for users who are new to our system
            if is_new_user:
                from .onboarding import create_demo_screen

                try:
                    await create_demo_screen(owner_id=user_id)
                    print(f"Created demo screen for user {user_id}")
                except Exception as e:
                    print(f"Failed to create demo screen for user {user_id}: {e}")

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


# ============== Stripe Webhooks ==============


def _get_plan_from_price(price_id: str) -> str:
    """Map Stripe price ID to plan name."""
    settings = get_settings()
    price_to_plan = {
        settings.STRIPE_PRICE_STARTER_MONTHLY: "starter",
        settings.STRIPE_PRICE_STARTER_YEARLY: "starter",
        settings.STRIPE_PRICE_PREMIUM_MONTHLY: "premium",
        settings.STRIPE_PRICE_PREMIUM_YEARLY: "premium",
    }
    return price_to_plan.get(price_id, "starter")  # Default to starter if unknown


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
):
    """Handle Stripe webhook events for subscription management.

    Events handled:
    - checkout.session.completed: Upgrade user plan after successful checkout
    - customer.subscription.created: Handle new/re-subscriptions (pricing table flow)
    - customer.subscription.updated: Sync subscription status changes
    - customer.subscription.deleted: Downgrade user to free plan
    - invoice.payment_failed: Mark subscription as past_due
    """
    settings = get_settings()

    # Only process in SaaS mode
    if settings.APP_MODE != AppMode.SAAS:
        raise HTTPException(status_code=404, detail="Not found")

    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=401, detail="Invalid signature") from None
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e!s}") from None

    event_type = event["type"]
    data = event["data"]["object"]

    db = get_database()

    # Handle checkout completion - upgrade plan
    if event_type == "checkout.session.completed":
        subscription_id = data.get("subscription")
        customer_id = data.get("customer")

        if subscription_id:
            # Get subscription to find the plan
            subscription = stripe.Subscription.retrieve(subscription_id)

            # Try to get user_id from metadata first (our checkout endpoint)
            # Fall back to looking up by customer_id (Pricing Table checkout)
            user_id = data.get("metadata", {}).get("user_id")
            user = None

            if user_id:
                user = await db.get_user(user_id)
            elif customer_id:
                user = await db.get_user_by_stripe_customer(customer_id)

            if user:
                # Get plan from subscription metadata or price
                plan = subscription.get("metadata", {}).get("plan")
                if not plan:
                    # Get plan from price ID
                    items = subscription.get("items", {}).get("data", [])
                    if items:
                        price_id = items[0].get("price", {}).get("id")
                        if price_id:
                            plan = _get_plan_from_price(price_id)
                plan = plan or "starter"

                await db.update_user_plan(
                    user_id=user["id"],
                    plan=plan,
                    subscription_id=subscription_id,
                    subscription_status="active",
                )

    # Handle new subscription created (backup for pricing table flow)
    elif event_type == "customer.subscription.created":
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        status = data.get("status")

        if customer_id and status in ("active", "trialing"):
            user = await db.get_user_by_stripe_customer(customer_id)
            if user:
                # Get plan from subscription items
                items = data.get("items", {}).get("data", [])
                plan = "starter"  # Default
                if items:
                    price_id = items[0].get("price", {}).get("id")
                    if price_id:
                        plan = _get_plan_from_price(price_id)

                await db.update_user_plan(
                    user_id=user["id"],
                    plan=plan,
                    subscription_id=subscription_id,
                    subscription_status="active",
                )

    # Handle subscription updates
    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        status = data.get("status")

        # Map Stripe status to our status
        status_map = {
            "active": "active",
            "past_due": "past_due",
            "canceled": "canceled",
            "unpaid": "past_due",
            "trialing": "active",
        }
        our_status = status_map.get(status, "inactive")

        # Get user by Stripe customer ID
        user = await db.get_user_by_stripe_customer(customer_id)
        if user:
            # Get plan from subscription items
            items = data.get("items", {}).get("data", [])
            plan = "starter"  # Default
            if items:
                price_id = items[0].get("price", {}).get("id")
                if price_id:
                    plan = _get_plan_from_price(price_id)

            await db.update_user_plan(
                user_id=user["id"],
                plan=plan if our_status == "active" else user.get("plan", "free"),
                subscription_id=subscription_id,
                subscription_status=our_status,
            )

    # Handle subscription cancellation
    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")

        # Get user by Stripe customer ID
        user = await db.get_user_by_stripe_customer(customer_id)
        if user:
            await db.update_user_plan(
                user_id=user["id"],
                plan="free",  # Downgrade to free
                subscription_id=None,
                subscription_status="canceled",
            )

    # Handle payment failures
    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")

        # Get user by Stripe customer ID
        user = await db.get_user_by_stripe_customer(customer_id)
        if user:
            await db.update_user_plan(
                user_id=user["id"],
                plan=user.get("plan", "free"),  # Keep current plan
                subscription_id=user.get("stripe_subscription_id"),
                subscription_status="past_due",
            )

    return {"success": True, "event": event_type}
