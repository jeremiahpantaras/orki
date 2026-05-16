from rest_framework.permissions import BasePermission


class IsFirebaseAuthenticated(BasePermission):
    """
    Grants access only when the request was authenticated via a valid
    Firebase ID token (i.e. request.user is a FirebaseUser with a uid).
    """

    message = "Authentication credentials were not provided or have expired."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and getattr(request.user, "is_authenticated", False)
            and getattr(request.user, "uid", None)
        )


# Backward-compatible alias — views that still reference IsSessionAuthenticated
# continue to work without renaming every import.
IsSessionAuthenticated = IsFirebaseAuthenticated


class IsSubscriber(BasePermission):
    """
    Grants access only to users with an active Firestore subscription.
    Backend-enforced: frontend paywall UI alone is not sufficient.
    """

    message = "Premium access required. Please upgrade your subscription to access exams & flashcards."

    def has_permission(self, request, view) -> bool:
        uid = getattr(request.user, "uid", None)
        if not uid:
            return False
        try:
            from services.firebase.firestore import get_subscription
            return get_subscription(uid).get("is_active", False)
        except Exception:
            return False
