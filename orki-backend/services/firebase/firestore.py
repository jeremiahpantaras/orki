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
    """Convert a Firestore Timestamp, datetime, or ISO-8601 string to an aware datetime."""
    if val is None:
        return None
    # google.cloud.firestore DatetimeWithNanoseconds is a datetime subclass
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=tz.utc)
    # Firestore Timestamp objects
    if hasattr(val, "ToDatetime"):
        return val.ToDatetime().replace(tzinfo=tz.utc)
    # ISO-8601 strings stored by the webhook handler via .isoformat()
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val)
            return dt if dt.tzinfo else dt.replace(tzinfo=tz.utc)
        except ValueError:
            pass
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


# ─── Payment History ───────────────────────────────────────────────────────────
#
# Subcollection: subscriptions/{firebase_uid}/transactions
# Append-only log of confirmed payments.

_PAYMENT_HISTORY_SUBCOLLECTION = "transactions"


def record_payment_history(uid: str, payment_data: dict) -> None:
    """
    Append a confirmed payment record to the user's transaction history.
    Called by the webhook handler after every successful payment.
    """
    db = get_firestore_client()
    ref = (
        db.collection(_SUBSCRIPTIONS_COLLECTION)
        .document(uid)
        .collection(_PAYMENT_HISTORY_SUBCOLLECTION)
    )
    ref.add({
        **payment_data,
        "recorded_at": firestore.SERVER_TIMESTAMP,
    })


def get_payment_history(uid: str) -> list:
    """
    Fetch the user's payment history from the transactions subcollection.

    Falls back to synthesising a single entry from the main subscription
    document for users who subscribed before payment history was introduced.
    """
    db = get_firestore_client()
    history_ref = (
        db.collection(_SUBSCRIPTIONS_COLLECTION)
        .document(uid)
        .collection(_PAYMENT_HISTORY_SUBCOLLECTION)
    )

    docs = list(
        history_ref.order_by(
            "payment_confirmed_at",
            direction=firestore.Query.DESCENDING,
        ).stream()
    )

    if docs:
        result = []
        for doc in docs:
            d = doc.to_dict()
            result.append({
                "id": doc.id,
                "amount_php": d.get("amount_php", 49.00),
                "currency": d.get("currency", "PHP"),
                "status": d.get("status", "paid"),
                "payment_method": d.get("payment_method", "unknown"),
                "payment_id": d.get("payment_id", ""),
                "plan_name": d.get("plan_name", "Orki Basic ₱49"),
                "payment_confirmed_at": _to_iso(d.get("payment_confirmed_at")),
                "start_date": _to_iso(d.get("start_date")),
                "expiry_date": _to_iso(d.get("expiry_date")),
            })
        return result

    # ── Fallback: synthesise from the subscription document for legacy users ──
    # This covers users who paid before the transactions subcollection existed,
    # and users whose webhook wrote data before payment_confirmed_at was added.
    sub = get_subscription(uid)
    if sub.get("status") == "active":
        # payment_confirmed_at was added later; fall back to start_date for
        # legacy subscriptions that were created before this field existed.
        confirmed_at = sub.get("payment_confirmed_at") or sub.get("start_date")
        if confirmed_at:
            return [
                {
                    "id": "legacy",
                    "amount_php": sub.get("amount_php", 49.00),
                    "currency": sub.get("currency", "PHP"),
                    "status": "paid",
                    "payment_method": sub.get("payment_method") or "unknown",
                    "payment_id": sub.get("paymongo_payment_id", "") or sub.get("payment_id", ""),
                    "plan_name": sub.get("plan_name", "Orki Basic ₱49"),
                    "payment_confirmed_at": confirmed_at,
                    "start_date": sub.get("start_date"),
                    "expiry_date": sub.get("expiry_date"),
                }
            ]

    return []


# ─── Account Management ────────────────────────────────────────────────────────


def deactivate_user(uid: str) -> None:
    """
    Soft-deactivate a user account by setting is_active=False in Firestore.
    The user can reactivate simply by signing in again.
    """
    db = get_firestore_client()
    db.collection(_USERS_COLLECTION).document(uid).update({
        "is_active": False,
        "deactivated_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })


def delete_user_data(uid: str) -> None:
    """
    Permanently delete all Firestore data associated with a user.
    Cascades into the payment history subcollection before removing parent docs.
    Does NOT delete the Firebase Auth account — the caller is responsible.
    """
    db = get_firestore_client()

    # Delete payment history subcollection first (Firestore requires explicit deletion)
    history_ref = (
        db.collection(_SUBSCRIPTIONS_COLLECTION)
        .document(uid)
        .collection(_PAYMENT_HISTORY_SUBCOLLECTION)
    )
    for doc in history_ref.stream():
        doc.reference.delete()

    # Delete top-level user documents
    db.collection(_USERS_COLLECTION).document(uid).delete()
    db.collection(_SUBSCRIPTIONS_COLLECTION).document(uid).delete()

    # Delete exam attempts and sessions
    for doc in db.collection("exam_attempts").where("user_id", "==", uid).stream():
        doc.reference.delete()

    for doc in db.collection("exam_sessions").where("user_id", "==", uid).stream():
        doc.reference.delete()

    # Delete analytics entries
    for doc in db.collection("analytics").where("userId", "==", uid).stream():
        doc.reference.delete()

