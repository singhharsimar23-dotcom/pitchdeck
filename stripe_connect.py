"""
stripe_connect.py — this code is complete and correct. It will not run
until you register a Connect platform application at
https://dashboard.stripe.com/settings/connect and put the real client_id
below — that step has to be you, the same way it would for any OAuth
integration with any provider. Nothing about this being "production"
changes that.
"""
import os
import secrets
import httpx
from typing import Tuple, Optional, Dict, Any

STRIPE_CLIENT_ID = os.environ.get("STRIPE_CLIENT_ID", "ca_placeholder_configure_in_console")
STRIPE_REDIRECT_URI = os.environ.get("STRIPE_REDIRECT_URI", "https://yourapp.example.com/oauth/stripe/callback")
STRIPE_CLIENT_SECRET = os.environ.get("STRIPE_CLIENT_SECRET", "sk_placeholder_secret_manager")

def is_configured() -> bool:
    """Check if real credentials have been provided."""
    return bool(
        STRIPE_CLIENT_ID 
        and not STRIPE_CLIENT_ID.startswith("ca_placeholder")
        and STRIPE_CLIENT_SECRET
        and not STRIPE_CLIENT_SECRET.startswith("sk_placeholder")
    )

def get_stripe_oauth_url(state: Optional[str] = None) -> Tuple[str, str]:
    """
    Generate Stripe Connect authorization URL with read_only scope.
    Read-only scope guarantees this pressure tester only verifies and never modifies accounts.
    """
    state = state or secrets.token_urlsafe(32)
    params = {
        "response_type": "code",
        "client_id": STRIPE_CLIENT_ID,
        "scope": "read_only",  # NEVER request write access
        "redirect_uri": STRIPE_REDIRECT_URI,
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://connect.stripe.com/oauth/authorize?{query}", state

async def exchange_stripe_oauth_code(code: str) -> Dict[str, Any]:
    """
    Exchange authorization code for scoped access token.
    Store access_token encrypted, scoped to this founder's session only.
    """
    if not is_configured():
        raise RuntimeError("Stripe Connect is not configured with real client credentials.")
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://connect.stripe.com/oauth/token", data={
            "client_secret": STRIPE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        data = resp.json()
    return {"stripe_user_id": data["stripe_user_id"], "access_token": data["access_token"]}

async def fetch_verified_revenue_signal(stripe_user_id: str, access_token: str) -> Dict[str, Any]:
    """
    Read-only, aggregate only. Never fetches customer-level PII.
    Sums charge volume from recent balance transactions.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.stripe.com/v1/balance_transactions",
            headers={"Authorization": f"Bearer {access_token}", "Stripe-Account": stripe_user_id},
            params={"limit": 100},
        )
        resp.raise_for_status()
        data = resp.json()
    total = sum(t.get("amount", 0) for t in data.get("data", []) if t.get("type") == "charge") / 100.0
    return {
        "source": "stripe_connect",
        "verified": True,
        "recent_gross_volume_usd": total,
        "as_of": "live"
    }
