from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import app.config as app_config
from app.domain.models import ErrorBody

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]

# Multipart boundaries and JSON metadata: slack beyond raw upload cap.
_BODY_SLACK_BYTES = 1_048_576


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject oversize requests early via Content-Length (use a proxy cap for chunked bodies)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl is not None:
                try:
                    size = int(cl)
                except ValueError:
                    pass
                else:
                    cap = app_config.max_upload_bytes() + _BODY_SLACK_BYTES
                    if size > cap:
                        body = ErrorBody(code="PAYLOAD_TOO_LARGE", detail="PAYLOAD_TOO_LARGE")
                        return JSONResponse(status_code=413, content=body.model_dump())
        return await call_next(request)
