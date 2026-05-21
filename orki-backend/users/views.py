"""
users/views.py — Firestore-backed API views.

All user data (profiles, subscriptions) is stored in Firestore.
Authentication uses Firebase ID tokens via the Authorization: Bearer header.
No Django session or SQLite is used for user-critical data.
"""
from datetime import datetime, timezone as tz
import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from firebase_admin import auth as firebase_auth

from core.permissions import IsFirebaseAuthenticated
from core.throttling import AuthRateThrottle
from services.firebase.firestore import (
    create_or_update_user_profile,
    deactivate_user,
    delete_user_data,
    get_payment_history,
    get_subscription,
    get_user_profile,
    update_subscription,
)
from services.paymongo import (
    PayMongoError,
    PayMongoService,
    WebhookHandler,
    WebhookVerificationError,
)

logger = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

_EXAM_TITLE = {
    "LEPT": "LPT",
    "CSE": "CSE Passer",
    "PmLE": "RPM",
    "CLE": "RCrim",
}

_VALID_EXAM_TYPES = {"LEPT", "CSE", "PmLE", "CLE"}


def _profile_response(profile: dict) -> dict:
    """Serialize a Firestore user profile dict into the API response shape."""
    exam_type = profile.get("exam_type", "")
    return {
        "uid": profile.get("uid", ""),
        "email": profile.get("email", ""),
        "display_name": profile.get("display_name", ""),
        "first_name": profile.get("first_name", ""),
        "last_name": profile.get("last_name", ""),
        "age": profile.get("age"),
        "exam_type": exam_type,
        "exam_date": profile.get("exam_date"),
        "onboarding_completed": bool(profile.get("onboarding_completed", False)),
        "professional_title": _EXAM_TITLE.get(exam_type, ""),
        "is_active": profile.get("is_active", True),
    }


# ─── Authentication ───────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    """
    POST /api/v1/auth/login/

    Verifies the Firebase ID token (via Authorization: Bearer header),
    idempotently creates or retrieves the Firestore user profile, and returns it.
    No Django session is created — auth is fully stateless.
    """

    permission_classes = [IsFirebaseAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        uid = request.user.uid
        existing = get_user_profile(uid)

        update_data: dict = {
            "email": request.user.email,
            "display_name": getattr(request.user, "display_name", ""),
        }
        # Auto-reactivate a previously deactivated account on sign-in
        if existing and existing.get("is_active") is False:
            update_data["is_active"] = True
            update_data["deactivated_at"] = None
            logger.info(f"Account reactivated on login: uid={uid}")

        profile = create_or_update_user_profile(uid, update_data)
        return Response(
            {
                "user": _profile_response(profile),
                "onboarding_complete": profile.get("onboarding_completed", False),
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/

    No-op for token-based auth.  The client clears Firebase Auth state
    client-side.  This endpoint exists for API consistency.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)


class SessionView(APIView):
    """
    GET /api/v1/auth/session/

    Returns the current user's Firestore profile.
    Creates the document (new user) if it doesn't exist yet.
    Called by the frontend on every page load via onAuthStateChanged.
    """

    permission_classes = [IsFirebaseAuthenticated]

    def get(self, request):
        uid = request.user.uid
        profile = get_user_profile(uid)

        if profile is None:
            # First app load after sign-up — bootstrap the profile document
            profile = create_or_update_user_profile(uid, {
                "email": request.user.email,
                "display_name": getattr(request.user, "display_name", ""),
                "onboarding_completed": False,
            })

        return Response(
            {
                "user": _profile_response(profile),
                "onboarding_complete": profile.get("onboarding_completed", False),
            }
        )


# ─── Profile ──────────────────────────────────────────────────────────────────

class ProfileView(APIView):
    """
    GET  /api/v1/users/me/   — Return the authenticated user's profile.
    PATCH /api/v1/users/me/  — Partially update mutable profile fields.
    """

    permission_classes = [IsFirebaseAuthenticated]

    def get(self, request):
        profile = get_user_profile(request.user.uid) or {}
        return Response(_profile_response(profile))

    def patch(self, request):
        # exam_type and onboarding_completed may only be set via onboarding
        immutable = {"exam_type", "onboarding_completed", "uid", "email"}
        mutable = {k: v for k, v in request.data.items() if k not in immutable}
        if not mutable:
            profile = get_user_profile(request.user.uid) or {}
            return Response(_profile_response(profile))
        profile = create_or_update_user_profile(request.user.uid, mutable)
        return Response(_profile_response(profile))


# ─── Onboarding ───────────────────────────────────────────────────────────────

class OnboardingView(APIView):
    """
    GET  /api/v1/users/onboarding/ — Onboarding completion status.
    POST /api/v1/users/onboarding/ — Save profile and mark onboarding complete.

    SAFE: if onboarding_completed is already True in Firestore, returns 400.
    Deployments never reset this flag because the data lives in Firestore.
    """

    permission_classes = [IsFirebaseAuthenticated]

    def get(self, request):
        profile = get_user_profile(request.user.uid) or {}
        return Response({"onboarding_completed": bool(profile.get("onboarding_completed", False))})

    def post(self, request):
        uid = request.user.uid
        profile = get_user_profile(uid) or {}

        if profile.get("onboarding_completed"):
            return Response(
                {"detail": "Onboarding already completed. Exam type cannot be changed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Input validation ──────────────────────────────────────────────────
        first_name = str(request.data.get("first_name", "")).strip()
        last_name = str(request.data.get("last_name", "")).strip()
        age = request.data.get("age")
        exam_type = str(request.data.get("exam_type", "")).strip()
        exam_date = request.data.get("exam_date") or None

        errors = {}
        if not first_name:
            errors["first_name"] = "This field is required."
        if not last_name:
            errors["last_name"] = "This field is required."
        if exam_type not in _VALID_EXAM_TYPES:
            errors["exam_type"] = f"Must be one of: {', '.join(sorted(_VALID_EXAM_TYPES))}."
        try:
            age_int = int(age)
            if not 1 <= age_int <= 120:
                errors["age"] = "Age must be between 1 and 120."
        except (TypeError, ValueError):
            errors["age"] = "A valid integer is required."

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        # ─────────────────────────────────────────────────────────────────────

        profile = create_or_update_user_profile(uid, {
            "first_name": first_name,
            "last_name": last_name,
            "age": age_int,
            "exam_type": exam_type,
            "exam_date": exam_date,
            "onboarding_completed": True,
        })

        return Response(
            {
                "detail": "Onboarding complete.",
                "user": _profile_response(profile),
            },
            status=status.HTTP_200_OK,
        )


# ─── Subscription & Payments ──────────────────────────────────────────────────

class SubscriptionStatusView(APIView):
    """
    GET /api/v1/users/subscription/

    Returns subscription status from Firestore.  Persists across deployments.
    """

    permission_classes = [IsFirebaseAuthenticated]

    def get(self, request):
        sub = get_subscription(request.user.uid)

        days_remaining = None
        expiry_iso = sub.get("expiry_date")
        if expiry_iso:
            try:
                expiry_dt = datetime.fromisoformat(expiry_iso)
                if expiry_dt.tzinfo is None:
                    expiry_dt = expiry_dt.replace(tzinfo=tz.utc)
                delta = expiry_dt - datetime.now(tz.utc)
                days_remaining = max(0, delta.days)
            except (ValueError, TypeError):
                pass

        return Response({
            "status": sub["status"],
            "is_active": sub["is_active"],
            "plan": sub.get("plan_name", "Orki Basic ₱49"),
            "payment_methods_allowed": ["GCash", "Maya", "Card", "QRPh"],
            "expires_at": expiry_iso,
            "days_remaining": days_remaining,
            "payment_method": sub.get("payment_method"),
        })


class CreateCheckoutView(APIView):
    """
    POST /api/v1/payments/checkout/

    Creates a PayMongo checkout session.  Stores checkout_id in Firestore
    so the webhook handler can match the payment to this user.
    """

    permission_classes = [IsFirebaseAuthenticated]

    def post(self, request):
        uid = request.user.uid
        email = request.user.email

        try:
            sub = get_subscription(uid)
            if sub.get("is_active"):
                return Response(
                    {"detail": "You already have an active subscription."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment_methods = request.data.get("payment_methods")
            logger.info(f"📲 Creating checkout for uid={uid} email={email}")

            checkout = PayMongoService.create_checkout(
                firebase_uid=uid,
                user_email=email,
                payment_methods=payment_methods,
            )

            # Persist checkout reference in Firestore for webhook correlation
            update_subscription(uid, {
                "paymongo_checkout_id": checkout["reference_id"],
            })

            logger.info(f"✓ Checkout created: {checkout['reference_id']}")
            return Response({
                "checkout_url": checkout["checkout_url"],
                "reference_id": checkout["reference_id"],
            })

        except PayMongoError as exc:
            logger.error(f"✗ PayMongo error: {exc}")
            return Response(
                {"detail": f"Payment service error: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error(f"✗ Unexpected checkout error: {exc}", exc_info=True)
            return Response(
                {"detail": "Failed to create checkout session."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class PayMongoWebhookView(APIView):
    """
    POST /api/v1/payments/webhook/

    CRITICAL: PayMongo webhook for payment confirmation.
    Updates the Firestore subscription document — survives all deployments.
    Requires AllowAny because PayMongo has no Firebase token.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        if not request.body:
            return Response({"error": "Empty request body"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = WebhookHandler.process_webhook(request.body, "")
            logger.info(f"Webhook processed: {result.get('message')}")
            return Response(result)

        except WebhookVerificationError as exc:
            logger.error(f"Webhook verification failed: {exc}")
            return Response({"error": "Webhook verification failed"}, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as exc:
            logger.error(f"Webhook processing error: {exc}", exc_info=True)
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPaymentView(APIView):
    """
    POST /api/v1/payments/verify/

    Webhook fallback: manually fetches the user's pending checkout session
    from PayMongo and activates the subscription in Firestore if payment
    is confirmed.

    Called by the frontend after a successful payment redirect when the
    webhook may not have fired yet (network delay, wrong URL, etc.).
    Uses the paymongo_checkout_id stored in Firestore at checkout creation.
    """

    permission_classes = [IsFirebaseAuthenticated]

    def post(self, request):
        uid = request.user.uid

        try:
            sub = get_subscription(uid)

            # Already active — return immediately, nothing to do.
            if sub.get("is_active"):
                expiry_iso = sub.get("expiry_date")
                days_remaining = None
                if expiry_iso:
                    try:
                        expiry_dt = datetime.fromisoformat(expiry_iso)
                        if expiry_dt.tzinfo is None:
                            expiry_dt = expiry_dt.replace(tzinfo=tz.utc)
                        delta = expiry_dt - datetime.now(tz.utc)
                        days_remaining = max(0, delta.days)
                    except (ValueError, TypeError):
                        pass
                return Response({
                    "success": True,
                    "status": "active",
                    "is_active": True,
                    "detail": "Subscription is already active.",
                    "expires_at": expiry_iso,
                    "days_remaining": days_remaining,
                })

            checkout_id = sub.get("paymongo_checkout_id", "")
            if not checkout_id:
                return Response(
                    {"success": False, "detail": "No pending checkout session found. Please initiate a new payment."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Fetch the checkout session from PayMongo and sync if paid.
            checkout_data = PayMongoService.get_checkout_session(checkout_id)
            result = WebhookHandler.sync_from_checkout_session(uid, checkout_data)

            if result.get("is_active"):
                expiry_iso = result.get("expiry_date")
                days_remaining = None
                if expiry_iso:
                    try:
                        expiry_dt = datetime.fromisoformat(expiry_iso)
                        if expiry_dt.tzinfo is None:
                            expiry_dt = expiry_dt.replace(tzinfo=tz.utc)
                        delta = expiry_dt - datetime.now(tz.utc)
                        days_remaining = max(0, delta.days)
                    except (ValueError, TypeError):
                        pass
                return Response({
                    "success": True,
                    "status": "active",
                    "is_active": True,
                    "detail": result.get("detail", "Subscription activated."),
                    "expires_at": expiry_iso,
                    "days_remaining": days_remaining,
                })

            return Response({
                "success": False,
                "status": result.get("status", "pending"),
                "is_active": False,
                "detail": result.get("detail", "Payment not yet confirmed."),
            })

        except PayMongoError as exc:
            logger.error(f"✗ PayMongo verify error uid={uid}: {exc}")
            return Response(
                {"success": False, "detail": f"Payment verification error: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error(f"✗ Verify payment error uid={uid}: {exc}", exc_info=True)
            return Response(
                {"success": False, "detail": "Failed to verify payment. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ─── Profile Account Management ───────────────────────────────────────────────


class SubscriptionHistoryView(APIView):
    """
    GET /api/v1/profile/subscription-history/

    Returns a user's payment history from the Firestore transactions
    subcollection.  Falls back to synthesising an entry from the current
    subscription document for users who subscribed before this feature.
    """

    permission_classes = [IsFirebaseAuthenticated]

    def get(self, request):
        history = get_payment_history(request.user.uid)
        return Response({"history": history})


class DeactivateAccountView(APIView):
    """
    POST /api/v1/profile/deactivate/

    Soft-deactivates the authenticated user's account by setting
    is_active=False in the Firestore user document.  The account is
    automatically reactivated the next time the user signs in.
    """

    permission_classes = [IsFirebaseAuthenticated]

    def post(self, request):
        uid = request.user.uid
        try:
            deactivate_user(uid)
            logger.info(f"Account deactivated: uid={uid}")
            return Response({"detail": "Account deactivated successfully."})
        except Exception as exc:
            logger.error(f"Failed to deactivate account uid={uid}: {exc}", exc_info=True)
            return Response(
                {"detail": "Failed to deactivate account. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteAccountView(APIView):
    """
    DELETE /api/v1/profile/delete-account/

    Permanently deletes the authenticated user's account:
    1. Removes all Firestore documents (profile, subscription, history,
       exam attempts, analytics).
    2. Deletes the Firebase Authentication account.

    This action is irreversible.  The frontend must require explicit
    email confirmation before calling this endpoint.
    """

    permission_classes = [IsFirebaseAuthenticated]

    def delete(self, request):
        uid = request.user.uid
        try:
            # Delete all Firestore data first
            delete_user_data(uid)
            # Delete the Firebase Auth account
            firebase_auth.delete_user(uid)
            logger.info(f"Account permanently deleted: uid={uid}")
            return Response({"detail": "Account permanently deleted."})
        except Exception as exc:
            logger.error(f"Failed to delete account uid={uid}: {exc}", exc_info=True)
            return Response(
                {"detail": "Failed to delete account. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

