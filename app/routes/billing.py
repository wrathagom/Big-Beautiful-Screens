"""Stripe billing API endpoints for subscription management.

These endpoints are only available in SaaS mode.
"""

import stripe
from fastapi import APIRouter, HTTPException

from ..auth import RequiredUser
from ..config import AppMode, get_settings
from ..db import get_database

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


def get_stripe_client():
    """Get configured Stripe client."""
    settings = get_settings()
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def get_price_id(plan: str, interval: str) -> str | None:
    """Get Stripe price ID for a plan and billing interval."""
    settings = get_settings()
    price_map = {
        ("pro", "monthly"): settings.STRIPE_PRICE_PRO_MONTHLY,
        ("pro", "yearly"): settings.STRIPE_PRICE_PRO_YEARLY,
        ("team", "monthly"): settings.STRIPE_PRICE_TEAM_MONTHLY,
        ("team", "yearly"): settings.STRIPE_PRICE_TEAM_YEARLY,
    }
    return price_map.get((plan, interval))


@router.post("/checkout")
async def create_checkout_session(
    user: RequiredUser,
    plan: str = "pro",
    interval: str = "monthly",
):
    """Create a Stripe Checkout session for plan upgrade.

    Args:
        plan: Target plan ("pro" or "team")
        interval: Billing interval ("monthly" or "yearly")

    Returns:
        checkout_url: URL to redirect user to Stripe Checkout
    """
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        raise HTTPException(status_code=404, detail="Billing not available in self-hosted mode")

    stripe_client = get_stripe_client()
    db = get_database()

    # Validate plan and interval
    if plan not in ("pro", "team"):
        raise HTTPException(status_code=400, detail="Invalid plan. Must be 'pro' or 'team'")
    if interval not in ("monthly", "yearly"):
        raise HTTPException(
            status_code=400, detail="Invalid interval. Must be 'monthly' or 'yearly'"
        )

    # Get price ID
    price_id = get_price_id(plan, interval)
    if not price_id:
        raise HTTPException(status_code=500, detail=f"Price not configured for {plan}/{interval}")

    # Get or create Stripe customer
    user_data = await db.get_user(user.user_id)
    customer_id = user_data.get("stripe_customer_id") if user_data else None

    if not customer_id:
        # Create new Stripe customer
        customer = stripe_client.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"user_id": user.user_id},
        )
        customer_id = customer.id
        await db.set_stripe_customer_id(user.user_id, customer_id)

    # Create checkout session
    session = stripe_client.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.APP_URL}/admin/usage?checkout=success",
        cancel_url=f"{settings.APP_URL}/admin/usage?checkout=canceled",
        metadata={
            "user_id": user.user_id,
            "plan": plan,
        },
        subscription_data={
            "metadata": {
                "user_id": user.user_id,
                "plan": plan,
            },
        },
    )

    return {"checkout_url": session.url}


@router.post("/portal")
async def create_portal_session(user: RequiredUser):
    """Create a Stripe Customer Portal session for subscription management.

    Returns:
        portal_url: URL to redirect user to Stripe Customer Portal
    """
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        raise HTTPException(status_code=404, detail="Billing not available in self-hosted mode")

    stripe_client = get_stripe_client()
    db = get_database()

    # Get customer ID
    user_data = await db.get_user(user.user_id)
    customer_id = user_data.get("stripe_customer_id") if user_data else None

    if not customer_id:
        raise HTTPException(
            status_code=400, detail="No billing account found. Please subscribe first."
        )

    # Create portal session
    session = stripe_client.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.APP_URL}/admin/usage",
    )

    return {"portal_url": session.url}


@router.post("/customer-session")
async def create_customer_session(user: RequiredUser):
    """Create a Stripe Customer Session for the pricing table.

    This ensures the pricing table uses the user's existing Stripe customer,
    rather than creating a new one on checkout.

    Returns:
        client_secret: Customer session client secret for the pricing table
    """
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        raise HTTPException(status_code=404, detail="Billing not available in self-hosted mode")

    stripe_client = get_stripe_client()
    db = get_database()

    # Get or create Stripe customer
    user_data = await db.get_user(user.user_id)
    customer_id = user_data.get("stripe_customer_id") if user_data else None

    if not customer_id:
        # Create new Stripe customer
        customer = stripe_client.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"user_id": user.user_id},
        )
        customer_id = customer.id
        await db.set_stripe_customer_id(user.user_id, customer_id)

    # Create customer session for pricing table
    session = stripe_client.CustomerSession.create(
        customer=customer_id,
        components={"pricing_table": {"enabled": True}},
    )

    return {"client_secret": session.client_secret}


@router.get("/subscription")
async def get_subscription_status(user: RequiredUser):
    """Get current subscription status for the user.

    Returns:
        plan: Current plan (free, pro, team)
        status: Subscription status (inactive, active, past_due, canceled)
        subscription_id: Stripe subscription ID (if active)
        customer_id: Stripe customer ID (if exists)
        email: Email address on file
        user_id: User ID
    """
    settings = get_settings()

    if settings.APP_MODE != AppMode.SAAS:
        return {
            "plan": "unlimited",
            "status": "active",
            "subscription_id": None,
            "customer_id": None,
            "email": None,
            "user_id": None,
        }

    db = get_database()
    user_data = await db.get_user(user.user_id)

    if not user_data:
        return {
            "plan": "free",
            "status": "inactive",
            "subscription_id": None,
            "customer_id": None,
            "email": user.email,
            "user_id": user.user_id,
        }

    return {
        "plan": user_data.get("plan", "free"),
        "status": user_data.get("subscription_status", "inactive"),
        "subscription_id": user_data.get("stripe_subscription_id"),
        "customer_id": user_data.get("stripe_customer_id"),
        "email": user_data.get("email"),
        "user_id": user.user_id,
    }
