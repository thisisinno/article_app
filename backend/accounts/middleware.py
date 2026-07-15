from django.conf import settings
from django.core import signing
from .models import AnonymousVisitor

COOKIE = "insight_visitor"
class AnonymousVisitorMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        visitor = None
        raw = request.COOKIES.get(COOKIE)
        if raw:
            try: visitor = AnonymousVisitor.objects.filter(pk=signing.loads(raw, salt=COOKIE)).first()
            except signing.BadSignature: pass
        if not visitor: visitor = AnonymousVisitor.objects.create()
        request.visitor = visitor
        response = self.get_response(request)
        if not raw:
            response.set_cookie(COOKIE, signing.dumps(str(visitor.pk), salt=COOKIE), max_age=31536000, httponly=True, samesite="Lax", secure=settings.ANONYMOUS_COOKIE_SECURE)
        return response
