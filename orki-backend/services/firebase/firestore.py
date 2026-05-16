"""
firestore.py — Firestore client singleton.

Provides a lazily-initialised Firestore client that reuses the single
Firebase Admin app.  Import ``get_firestore_client`` wherever you need
to read from or write to Firestore.

Usage::

    from services.firebase.firestore import get_firestore_client

    db = get_firestore_client()
    doc = db.collection("questions").document("ENG-001").get()
"""
from __future__ import annotations

from datetime import datetime, timezone as tz

import firebase_admin
from firebase_admin import firestore

from .firebase_admin import get_firebase_app

_client = None


def get_firestore_client():
    """
    Return an authenticated Firestore client (initialised once).

    Ensures firebase_admin.initialize_app() has been called before
    constructing the client, following the recommended pattern::

        firebase_admin.initialize_app(cred)
        db = firestore.client()
    """
    global _client
    if _client is not None:
        return _client

    # Guarantee the Admin app is initialised before building the client
    app = get_firebase_app()
    if app is None:
        raise RuntimeError(
            "Firebase Admin app failed to initialise. "
            "Check FIREBASE_CREDENTIALS_PATH and FIREBASE_PROJECT_ID in your .env."
        )

    _client = firestore.client(app=app)
    if _client is None:
        raise RuntimeError(
            "firestore.client() returned None — ensure the service account belongs "
            "to the correct Firebase project and Firestore is enabled."
        )
    return _client


# ─── User Profiles ─────────────────────────────────────────────────────────────
#
# Collection: users/{firebase_uid}
# This is the SINGLE SOURCE OF TRUTH for user profile data.
# It survives all backend deployments because it lives in Firestore, not SQLite.

_USERS_COLLECTION = "users"
_SUBSCRIPTIONS_COLLECTION = "subscriptions"


def get_user_profile(uid: str) -> dict | None:
    """
    Fetch a user profile from Firestore by Firebase UID.
    Returns None if the document does not exist.
    """
    db = get_firestore_client()
    doc = db.collection(_USERS_COLLECTION).document(uid).get()
    if not doc.exists:
        return None
    return {"uid": uid, **doc.to_dict()}


def create_or_update_user_profile(uid: str, data: dict) -> dict:
    """
    Idempotent create/update for a user profile document.

    - First call (new user): writes all fields plus created_at.
    - Subsequent calls: merges only the provided keys using update().
      Existing fields NOT in `data` are never overwritten.

    This is safe to call on every login — it will not reset onboarding_completed
    or any other field that is not explicitly included in `data`.
    """
    db = get_firestore_client()
    ref = db.collection(_USERS_COLLECTION).document(uid)
    existing = ref.get()

    if not existing.exists:
        ref.set({
            **data,
            "onboarding_completed": data.get("onboarding_completed", False),
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
    else:
        ref.update({
            **data,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

    return get_user_profile(uid) or {}


# ─── Subscriptions ─────────────────────────────────────────────────────────────
#
# Collection: subscriptions/{firebase_uid}
# Subscription status persists across deployments — it lives in Firestore, not SQLite.


def _to_dt(val) -> datetime | None:
    """Convert a Firestore Timestamp or datetime-like to an aware datetime."""
    if val is None:
        return None
    # google.cloud.firestore DatetimeWithNanoseconds is a datetime subclass
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=tz.utc)
    # Fallback for Timestamp objects with ToDatetime()
    if hasattr(val, "ToDatetime"):
        return val.ToDatetime().replace(tzinfo=tz.utc)
    return None


def _to_iso(val) -> str | None:
    """Convert a Firestore Timestamp / datetime to ISO-8601 string."""
    dt = _to_dt(val)
    return dt.isoformat() if dt else None


def get_subscription(uid: str) -> dict:
    """
    Fetch subscription data from Firestore for a given Firebase UID.
    Returns a default "no_subscription" structure if the document does not exist.
    The returned dict always includes a computed `is_active` boolean.
    """
    db = get_firestore_client()
    doc = db.collection(_SUBSCRIPTIONS_COLLECTION).document(uid).get()

    if not doc.exists:
        return {
            "status": "no_subscription",
            "is_active": False,
            "plan_name": "Orki Basic ₱49",
            "amount_php": 49.00,
            "currency": "PHP",
            "payment_method": None,
            "paymongo_checkout_id": "",
            "paymongo_payment_id": "",
            "paymongo_reference_number": "",
            "last_webhook_event_id": "",
            "start_date": None,
            "expiry_date": None,
            "payment_confirmed_at": None,
        }

    data = doc.to_dict()
    now = datetime.now(tz.utc)

    expiry_dt = _to_dt(data.get("expiry_date"))
    status_val = data.get("status", "no_subscription")
    is_active = (
        status_val == "active"
        and expiry_dt is not None
        and expiry_dt > now
    )

    return {
        "status": status_val,
        "is_active": is_active,
        "plan_name": data.get("plan_name", "Orki Basic ₱49"),
        "amount_php": data.get("amount_php", 49.00),
        "currency": data.get("currency", "PHP"),
        "payment_method": data.get("payment_method") or None,
        "paymongo_checkout_id": data.get("paymongo_checkout_id", ""),
        "paymongo_payment_id": data.get("paymongo_payment_id", ""),
        "paymongo_reference_number": data.get("paymongo_reference_number", ""),
        "last_webhook_event_id": data.get("last_webhook_event_id", ""),
        "start_date": _to_iso(data.get("start_date")),
        "expiry_date": _to_iso(data.get("expiry_date")),
        "payment_confirmed_at": _to_iso(data.get("payment_confirmed_at")),
    }


def update_subscription(uid: str, data: dict) -> None:
    """
    Create or merge-update a subscription document in Firestore.
    Uses set(merge=True) so partial updates never overwrite unrelated fields.
    Safe to call from both the checkout flow and the PayMongo webhook handler.
    """
    db = get_firestore_client()
    ref = db.collection(_SUBSCRIPTIONS_COLLECTION).document(uid)
    ref.set(
        {**data, "updated_at": firestore.SERVER_TIMESTAMP},
        merge=True,
    )

