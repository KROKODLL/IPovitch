from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import hsts_max_age_seconds

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]

_PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), microphone=(), payment=(), usb=(), "
    "interest-cohort=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", _PERMISSIONS_POLICY)
        hsts = hsts_max_age_seconds()
        if hsts is not None:
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={hsts}; includeSubDomains",
            )
        path = request.url.path
        no_cache = (
            path.startswith("/v1")
            or path.startswith("/docs")
            or path in ("/openapi.json", "/redoc")
        )
        if no_cache:
            response.headers.setdefault("Cache-Control", "no-store, max-age=0")
            response.headers.setdefault("Pragma", "no-cache")
        return response
