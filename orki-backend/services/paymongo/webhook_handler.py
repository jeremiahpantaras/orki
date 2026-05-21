"""
PayMongo Webhook Handler
========================

CRITICAL: This is the ONLY source of truth for payment confirmation.
Writes subscription status to Firestore — persists across all deployments.

Process:
1. Receive webhook from PayMongo
2. Verify webhook signature
3. Check idempotency (webhook event ID)
4. Extract firebase_uid from checkout metadata
5. Mark subscription as ACTIVE with 30-day expiry in Firestore
"""
import json
import logging
from datetime import datetime, timedelta, timezone as tz

from services.firebase.firestore import get_subscription, record_payment_history, update_subscription
from .payment_service import PayMongoError, PayMongoService, WebhookVerificationError

logger = logging.getLogger(__name__)


def _parse_paid_at(checkout_attributes: dict, payment_attributes: dict) -> datetime:
    """
    Extract the paid_at timestamp from PayMongo payload.
    Prefers checkout_attributes.paid_at, falls back to payment_attributes.paid_at,
    then to server time.  PayMongo returns paid_at as a UNIX integer.
    """
    paid_at_unix = checkout_attributes.get("paid_at") or payment_attributes.get("paid_at")
    if paid_at_unix:
        try:
            return datetime.fromtimestamp(int(paid_at_unix), tz=tz.utc)
        except (TypeError, ValueError, OSError):
            pass
    return datetime.now(tz.utc)


def _extract_payment_method(checkout_attributes: dict, payment_attributes: dict) -> str:
    """
    Extract the payment method string from PayMongo checkout session data.
    PayMongo puts this in checkout_attributes.payment_method_used for
    checkout sessions, and payment_attributes.payment_method_type for
    individual payment objects.  Falls back to "unknown".
    """
    return (
        checkout_attributes.get("payment_method_used")
        or payment_attributes.get("payment_method_type")
        or "unknown"
    )


class WebhookHandler:
    """Handles PayMongo webhook events — writes to Firestore."""

    @staticmethod
    def handle_checkout_session_payment_paid(event_data: dict) -> dict:
        """
        Handle 'checkout_session.payment.paid' webhook event.
        Activates subscription in Firestore.
        """
        event_id = event_data.get("data", {}).get("id")
        logger.info(f"Processing webhook event: {event_id}")

        if not event_id:
            raise ValueError("Missing event ID")

        checkout_session = event_data.get("data", {}).get("attributes", {}).get("data", {})
        checkout_id = checkout_session.get("id", "")
        checkout_attributes = checkout_session.get("attributes", {})
        metadata = checkout_attributes.get("metadata", {})

        firebase_uid = metadata.get("firebase_uid")
        user_email = metadata.get("user_email", "")

        if not firebase_uid:
            logger.error(f"Missing firebase_uid in webhook metadata: {metadata}")
            raise ValueError("Missing firebase_uid in webhook metadata")

        # Extract payment info
        payments = checkout_attributes.get("payments", [])
        if not payments:
            raise ValueError("No payments in checkout")

        payment_data = payments[0]
        payment_id = payment_data.get("id", "")
        payment_attributes = payment_data.get("attributes", {})
        payment_status = payment_attributes.get("status")

        if payment_status != "paid":
            raise ValueError(f"Payment not in 'paid' status: {payment_status}")

        # Correct payment method extraction — PayMongo uses payment_method_used
        # on the checkout session, NOT a nested object on the payment.
        payment_method = _extract_payment_method(checkout_attributes, payment_attributes)

        # Use PayMongo's paid_at timestamp so start/expiry match the real payment time.
        paid_at = _parse_paid_at(checkout_attributes, payment_attributes)
        expiry = paid_at + timedelta(days=30)

        # Payment intent ID for audit trail
        payment_intent = checkout_attributes.get("payment_intent") or {}
        payment_intent_id = payment_intent.get("id", "") if isinstance(payment_intent, dict) else ""

        # ── Idempotency check ──────────────────────────────────────────────
        existing = get_subscription(firebase_uid)
        if existing.get("last_webhook_event_id") == event_id:
            logger.warning(f"Duplicate webhook event {event_id} for uid={firebase_uid}")
            return {
                "success": True,
                "message": "Webhook already processed (idempotent)",
                "firebase_uid": firebase_uid,
                "event_id": event_id,
            }

        # ── Activate subscription in Firestore ────────────────────────────
        update_subscription(firebase_uid, {
            "status": "active",
            "plan_name": "Orki Basic ₱49",
            "amount_php": 49.00,
            "payment_method": payment_method,
            "payment_id": payment_id,
            "paymongo_payment_id": payment_id,
            "paymongo_checkout_id": checkout_id,
            "paymongo_payment_intent_id": payment_intent_id,
            "last_webhook_event_id": event_id,
            "start_date": paid_at.isoformat(),
            "expiry_date": expiry.isoformat(),
            "payment_confirmed_at": paid_at.isoformat(),
            "user_email": user_email,
        })

        # ── Append to payment history (append-only audit log) ─────────────
        record_payment_history(firebase_uid, {
            "amount_php": 49.00,
            "currency": "PHP",
            "status": "paid",
            "payment_method": payment_method,
            "payment_id": payment_id,
            "plan_name": "Orki Basic ₱49",
            "payment_confirmed_at": paid_at.isoformat(),
            "start_date": paid_at.isoformat(),
            "expiry_date": expiry.isoformat(),
            "user_email": user_email,
            "webhook_event_id": event_id,
            "paymongo_checkout_id": checkout_id,
        })

        logger.info(
            f"Subscription ACTIVE | uid={firebase_uid} | method={payment_method} | expiry={expiry.date()}"
        )

        return {
            "success": True,
            "message": "Subscription activated successfully",
            "firebase_uid": firebase_uid,
            "user_email": user_email,
            "event_id": event_id,
            "expiry_date": expiry.isoformat(),
        }

    @staticmethod
    def sync_from_checkout_session(firebase_uid: str, checkout_data: dict) -> dict:
        """
        Manually sync a completed PayMongo checkout session to Firestore.

        Used as a webhook fallback: called by VerifyPaymentView when the
        webhook hasn't fired yet (network failure, wrong URL, etc.).

        Args:
            firebase_uid: Authenticated user's Firebase UID
            checkout_data: The "data" object from GET /v1/checkout_sessions/{id}

        Returns:
            dict with success, status, is_active, and detail keys
        """
        checkout_id = checkout_data.get("id", "")
        checkout_attributes = checkout_data.get("attributes", {})
        checkout_status = checkout_attributes.get("status", "")

        if checkout_status != "completed":
            logger.info(f"Checkout {checkout_id} not completed (status={checkout_status}) for uid={firebase_uid}")
            return {
                "success": False,
                "status": checkout_status,
                "is_active": False,
                "detail": f"Payment not yet completed (checkout status: {checkout_status}). Please wait a moment.",
            }

        metadata = checkout_attributes.get("metadata", {})
        uid_from_meta = metadata.get("firebase_uid", "")
        if uid_from_meta and uid_from_meta != firebase_uid:
            raise ValueError("firebase_uid mismatch between auth token and checkout metadata")

        user_email = metadata.get("user_email", "")

        payments = checkout_attributes.get("payments", [])
        if not payments:
            return {
                "success": False,
                "is_active": False,
                "detail": "No payments found in checkout session.",
            }

        payment_data = payments[0]
        payment_id = payment_data.get("id", "")
        payment_attributes = payment_data.get("attributes", {})
        payment_status = payment_attributes.get("status", "")

        if payment_status != "paid":
            return {
                "success": False,
                "status": payment_status,
                "is_active": False,
                "detail": f"Payment not confirmed (payment status: {payment_status}).",
            }

        # ── Idempotency: already active for this checkout session ──────────
        existing = get_subscription(firebase_uid)
        if existing.get("is_active") and existing.get("paymongo_checkout_id") == checkout_id:
            logger.info(f"Subscription already active for uid={firebase_uid} checkout={checkout_id}")
            return {
                "success": True,
                "status": "active",
                "is_active": True,
                "detail": "Subscription is already active.",
                "expiry_date": existing.get("expiry_date"),
            }

        payment_method = _extract_payment_method(checkout_attributes, payment_attributes)
        paid_at = _parse_paid_at(checkout_attributes, payment_attributes)
        expiry = paid_at + timedelta(days=30)

        payment_intent = checkout_attributes.get("payment_intent") or {}
        payment_intent_id = payment_intent.get("id", "") if isinstance(payment_intent, dict) else ""

        # ── Activate subscription ──────────────────────────────────────────
        update_subscription(firebase_uid, {
            "status": "active",
            "plan_name": "Orki Basic ₱49",
            "amount_php": 49.00,
            "payment_method": payment_method,
            "payment_id": payment_id,
            "paymongo_payment_id": payment_id,
            "paymongo_checkout_id": checkout_id,
            "paymongo_payment_intent_id": payment_intent_id,
            "start_date": paid_at.isoformat(),
            "expiry_date": expiry.isoformat(),
            "payment_confirmed_at": paid_at.isoformat(),
            "user_email": user_email,
        })

        # ── Append to payment history ──────────────────────────────────────
        record_payment_history(firebase_uid, {
            "amount_php": 49.00,
            "currency": "PHP",
            "status": "paid",
            "payment_method": payment_method,
            "payment_id": payment_id,
            "plan_name": "Orki Basic ₱49",
            "payment_confirmed_at": paid_at.isoformat(),
            "start_date": paid_at.isoformat(),
            "expiry_date": expiry.isoformat(),
            "user_email": user_email,
            "paymongo_checkout_id": checkout_id,
        })

        logger.info(
            f"Subscription ACTIVE (manual verify) | uid={firebase_uid} | method={payment_method} | expiry={expiry.date()}"
        )

        return {
            "success": True,
            "status": "active",
            "is_active": True,
            "detail": "Subscription activated successfully.",
            "expiry_date": expiry.isoformat(),
        }

    @staticmethod
    def process_webhook(request_body: bytes, signature_header: str) -> dict:
        """
        Main webhook processing entry point.

        Args:
            request_body: Raw request body as bytes
            signature_header: X-Paymongo-Signature header value

        Returns:
            Response dict

        Raises:
            WebhookVerificationError if signature is invalid
            PayMongoError if processing fails
        """
        # ── Verify signature ──────────────────────────────────────────────
        try:
            if not PayMongoService.verify_webhook_signature(request_body, signature_header):
                raise WebhookVerificationError("Invalid webhook signature")
        except WebhookVerificationError:
            raise
        except Exception as exc:
            raise WebhookVerificationError(f"Webhook verification failed: {exc}") from exc

        # ── Parse event ───────────────────────────────────────────────────
        try:
            event = PayMongoService.parse_webhook_event(request_body)
        except Exception as exc:
            raise PayMongoError(f"Failed to parse webhook: {exc}") from exc

        # ── Route ─────────────────────────────────────────────────────────
        event_type = event.get("data", {}).get("attributes", {}).get("type")
        logger.info(f"Webhook event type: {event_type}")

        if event_type == "checkout_session.payment.paid":
            return WebhookHandler.handle_checkout_session_payment_paid(event)

        logger.info(f"Ignoring webhook event type: {event_type}")
        return {"success": True, "message": f"Event type '{event_type}' ignored"}


