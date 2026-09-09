"""Security response headers not already covered by SecurityMiddleware.

Django's SecurityMiddleware handles nosniff, HSTS, and SSL redirect.
XFrameOptionsMiddleware handles framing. This middleware adds a
restrictive Content-Security-Policy and Permissions-Policy, since
Femtoboard has no third-party script/style/media origins to allow
(design doc section 80.7, 80.8).
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

_CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "media-src 'self'",
        "font-src 'self'",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "worker-src 'self'",
    ]
)

_PERMISSIONS_POLICY = ", ".join(
    [
        "camera=()",
        "microphone=()",
        "geolocation=()",
        "payment=()",
        "usb=()",
        "interest-cohort=()",
    ]
)


class SecurityHeadersMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", _CSP)
        response.headers.setdefault("Permissions-Policy", _PERMISSIONS_POLICY)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response
