import json
import uuid
from django.http import JsonResponse

class ApiResponseMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        try:
            response = self.get_response(request)
        except Exception:
            if request.path.startswith("/api/v1/"):
                response = JsonResponse({"error":{"code":"server_error","message":"The server could not complete the request.","request_id":request.request_id}}, status=500)
            else: raise
        if request.path.startswith("/api/v1/") and "application/json" not in response.get("Content-Type", ""):
            messages={404:("not_found","Not found"),405:("method_not_allowed","Method not allowed")}
            code,message=messages.get(response.status_code,("invalid_response","The server returned an invalid response."))
            response=JsonResponse({"error":{"code":code,"message":message,"request_id":request.request_id}},status=response.status_code)
        response["X-Request-ID"] = request.request_id
        return response
