import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.domain.models import ErrorBody

RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]

access_log = logging.getLogger("ipovtich.access")
error_log = logging.getLogger("ipovtich.error")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            error_log.exception(
                "unhandled_exception request_id=%s method=%s path=%s duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            access_log.error(
                "request_id=%s method=%s path=%s status=500 duration_ms=%.2f internal=1",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            payload = ErrorBody(code="INTERNAL_ERROR", detail="INTERNAL_ERROR").model_dump()
            out = JSONResponse(status_code=500, content=payload)
            out.headers.setdefault("X-Request-ID", request_id)
            return out
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers.setdefault("X-Request-ID", request_id)
        msg = (
            f"request_id={request_id} method={request.method} path={request.url.path} "
            f"status={response.status_code} duration_ms={duration_ms:.2f}"
        )
        if response.status_code >= 400:
            access_log.warning(msg)
        else:
            access_log.info(msg)
        return response
