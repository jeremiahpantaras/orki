from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to guarantee a consistent JSON
    error envelope: { "detail": "..." }.
    """
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception – print traceback to terminal and return a generic 500
        import traceback
        traceback.print_exc()
        return Response(
            {"detail": "An unexpected error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
