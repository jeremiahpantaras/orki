class FirestoreUserMiddleware:
    """
    Replaces the old SessionUserMiddleware.

    With stateless Firebase token auth there is no SQLite session to look up.
    This middleware ensures ``request.user_profile`` is initialised to None
    before each request.  Views that need the Firestore profile fetch it
    directly via ``request.user.uid``.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user_profile = None
        return self.get_response(request)
