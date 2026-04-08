"""
Stripe billing integration — subscription tiers for Pharma Expert.

Tiers:
  - FREE:     Limited (5 AI calls/day, no local GGUF, no WHO INN access)
  - STARTER:  $9/mo  — 100 AI calls/day, local GGUF, WHO INN
  - PRO:      $29/mo — Unlimited AI, priority, email support
  - ENTERPRISE: $99/mo — Multi-tenant, custom INN, dedicated support

Env vars:
  STRIPE_SECRET_KEY      — sk_live_... or sk_test_...
  STRIPE_WEBHOOK_SECRET  — whsec_...
  STRIPE_PRICE_STARTER   — price_... (starter plan)
  STRIPE_PRICE_PRO       — price_...
  STRIPE_PRICE_ENTERPRISE — price_...
"""
import os
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request

import db
from auth import get_current_user

logger = logging.getLogger("billing_routes")
router = APIRouter(prefix="/api/billing", tags=["billing"])

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

PLANS = {
    "free": {
        "name": "Free",
        "price": 0,
        "currency": "USD",
        "limits": {"ai_calls_per_day": 5, "local_gguf": False, "who_inn": False, "support": "none"},
    },
    "starter": {
        "name": "Starter",
        "price": 9,
        "currency": "USD",
        "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER"),
        "limits": {"ai_calls_per_day": 100, "local_gguf": True, "who_inn": True, "support": "community"},
    },
    "pro": {
        "name": "Pro",
        "price": 29,
        "currency": "USD",
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO"),
        "limits": {"ai_calls_per_day": -1, "local_gguf": True, "who_inn": True, "support": "email"},
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 99,
        "currency": "USD",
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE"),
        "limits": {"ai_calls_per_day": -1, "local_gguf": True, "who_inn": True, "support": "dedicated", "multi_tenant": True},
    },
}


def is_configured() -> bool:
    return bool(STRIPE_SECRET)


@router.get("/plans")
async def list_plans():
    """Public: list available plans."""
    return {"plans": PLANS, "stripe_configured": is_configured()}


@router.get("/subscription")
async def my_subscription(current_user: Dict = Depends(get_current_user)):
    """Get current user's subscription info."""
    try:
        conn = db.connect_db()
        conn.row_factory = db.sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE,
                plan TEXT DEFAULT 'free',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                status TEXT DEFAULT 'active',
                current_period_end TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("SELECT * FROM user_subscriptions WHERE user_id = ?", (current_user.get("id", ""),))
        row = cur.fetchone()
        conn.close()

        if not row:
            return {"plan": "free", "status": "active", "limits": PLANS["free"]["limits"]}

        plan_key = row["plan"]
        plan = PLANS.get(plan_key, PLANS["free"])
        return {
            "plan": plan_key,
            "plan_name": plan["name"],
            "status": row["status"],
            "current_period_end": row["current_period_end"],
            "limits": plan["limits"],
        }
    except Exception as e:
        return {"plan": "free", "status": "active", "limits": PLANS["free"]["limits"], "error": str(e)}


@router.post("/checkout")
async def create_checkout_session(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Create Stripe checkout session for upgrade."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="Billing хизмати ҳали фаолланмаган")

    plan_key = payload.get("plan", "starter")
    if plan_key not in PLANS or plan_key == "free":
        raise HTTPException(status_code=400, detail="Нотўғри план")

    plan = PLANS[plan_key]
    price_id = plan.get("stripe_price_id")
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Stripe price ID для {plan_key} ўрнатилмаган")

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=payload.get("success_url", "https://www.pharmtech.info/billing?success=true"),
            cancel_url=payload.get("cancel_url", "https://www.pharmtech.info/billing?canceled=true"),
            customer_email=current_user.get("email"),
            client_reference_id=str(current_user.get("id", "")),
            metadata={"user_id": str(current_user.get("id", "")), "plan": plan_key},
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except ImportError:
        raise HTTPException(status_code=503, detail="stripe пакет ўрнатилмаган")
    except Exception as e:
        logger.exception("checkout failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    if not is_configured() or not STRIPE_WEBHOOK_SECRET:
        return {"ok": False, "error": "not configured"}

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        import stripe
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error(f"[webhook] signature verify failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    try:
        conn = db.connect_db()
        cur = conn.cursor()
        if event_type == "checkout.session.completed":
            user_id = data.get("client_reference_id")
            customer_id = data.get("customer")
            subscription_id = data.get("subscription")
            plan = (data.get("metadata") or {}).get("plan", "starter")
            if user_id:
                cur.execute("""
                    INSERT OR REPLACE INTO user_subscriptions
                        (user_id, plan, stripe_customer_id, stripe_subscription_id, status, updated_at)
                    VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
                """, (user_id, plan, customer_id, subscription_id))
                conn.commit()
                logger.info(f"[webhook] activated {plan} for user {user_id}")

        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
            sub_id = data.get("id")
            status = data.get("status", "inactive")
            cur.execute(
                "UPDATE user_subscriptions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE stripe_subscription_id = ?",
                (status, sub_id)
            )
            conn.commit()

        conn.close()
    except Exception as e:
        logger.error(f"[webhook] DB error: {e}")

    return {"ok": True}
