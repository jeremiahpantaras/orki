from django.urls import path

from .views import (
    CreateCheckoutView,
    DeactivateAccountView,
    DeleteAccountView,
    LoginView,
    LogoutView,
    OnboardingView,
    PayMongoWebhookView,
    ProfileView,
    SessionView,
    SubscriptionHistoryView,
    SubscriptionStatusView,
    VerifyPaymentView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/session/", SessionView.as_view(), name="auth-session"),
    path("users/me/", ProfileView.as_view(), name="user-profile"),
    path("users/onboarding/", OnboardingView.as_view(), name="user-onboarding"),
    path("users/subscription/", SubscriptionStatusView.as_view(), name="subscription-status"),
    path("payments/checkout/", CreateCheckoutView.as_view(), name="create-checkout"),
    path("payments/webhook/", PayMongoWebhookView.as_view(), name="paymongo-webhook"),
    path("payments/verify/", VerifyPaymentView.as_view(), name="verify-payment"),
    # ── Profile account management ──────────────────────────────────────────
    path("profile/subscription-history/", SubscriptionHistoryView.as_view(), name="subscription-history"),
    path("profile/deactivate/", DeactivateAccountView.as_view(), name="deactivate-account"),
    path("profile/delete-account/", DeleteAccountView.as_view(), name="delete-account"),
]
