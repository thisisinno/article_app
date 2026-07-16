import logging
import uuid

from django.http import JsonResponse


logger = logging.getLogger("jesca.api")
API_PREFIX = "/api/v1/"


class ApiResponseMiddleware:
    """Keep the public API JSON-only while leaving admin/media/static untouched."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        is_api = request.path.startswith(API_PREFIX)
        try:
            response = self.get_response(request)
        except Exception as exc:
            if not is_api:
                raise
            logger.exception(
                "Unhandled API exception",
                extra={
                    "request_id": request.request_id,
                    "method": request.method,
                    "path": request.path,
                    "status": 500,
                    "exception_type": type(exc).__name__,
                },
            )
            response = self._error(
                request, 500, "server_error", "The server could not complete the request."
            )

        if is_api and not self._is_json(response):
            code, message = {
                400: ("bad_request", "Bad request"),
                401: ("authentication_required", "Please sign in to continue."),
                403: ("forbidden", "Forbidden"),
                404: ("not_found", "Not found"),
                405: ("method_not_allowed", "Method not allowed"),
                409: ("conflict", "Conflict"),
                429: ("rate_limited", "Too many requests"),
                500: ("server_error", "The server could not complete the request."),
            }.get(response.status_code, ("invalid_response", "The server returned an invalid response."))
            logger.warning(
                "Normalized non-JSON API response",
                extra={
                    "request_id": request.request_id,
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "exception_type": None,
                },
            )
            response = self._error(request, response.status_code, code, message)

        response["X-Request-ID"] = request.request_id
        return response

    @staticmethod
    def _is_json(response):
        content_type = response.get("Content-Type", "").lower().split(";", 1)[0].strip()
        return content_type in {"application/json", "application/problem+json"}

    @staticmethod
    def _error(request, status, code, message):
        return JsonResponse(
            {"error": {"code": code, "message": message, "request_id": request.request_id}},
            status=status,
        )
