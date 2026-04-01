from collections import deque
from time import monotonic

from fastapi import HTTPException, Request, status


class AuthLoginRateLimiter:
    """Sliding-window limiter per client IP for credential stuffing resistance."""

    def __init__(self, max_per_window: int, window_seconds: float = 60.0) -> None:
        self._max = max_per_window
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def allow(self, ip: str) -> bool:
        now = monotonic()
        dq = self._hits.setdefault(ip, deque())
        while dq and now - dq[0] > self._window:
            dq.popleft()
        if len(dq) >= self._max:
            return False
        dq.append(now)
        return True


async def enforce_login_rate_limit(request: Request) -> None:
    rl = getattr(request.app.state, "auth_login_rl", None)
    if rl is None:
        return
    ip = request.client.host if request.client else "unknown"
    if not rl.allow(ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="LOGIN_RATE_LIMITED",
        )
