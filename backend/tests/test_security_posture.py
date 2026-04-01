import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.auth_jwt import JWT_ISSUER
from app.auth_rate_limit import AuthLoginRateLimiter, enforce_login_rate_limit
from app.config import hsts_max_age_seconds, login_rate_limit_per_minute
from app.main import create_app
from app.max_body import MaxBodySizeMiddleware

JWT_SECRET = "a" * 32


def test_login_rate_limit_per_minute_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IPOVITCH_LOGIN_RATE_PER_MINUTE", raising=False)
    assert login_rate_limit_per_minute() == 20
    monkeypatch.setenv("IPOVITCH_LOGIN_RATE_PER_MINUTE", "0")
    assert login_rate_limit_per_minute() is None
    monkeypatch.setenv("IPOVITCH_LOGIN_RATE_PER_MINUTE", "not-int")
    assert login_rate_limit_per_minute() == 20
    monkeypatch.setenv("IPOVITCH_LOGIN_RATE_PER_MINUTE", "-3")
    assert login_rate_limit_per_minute() is None
    monkeypatch.setenv("IPOVITCH_LOGIN_RATE_PER_MINUTE", "99999")
    assert login_rate_limit_per_minute() == 500
    monkeypatch.setenv("IPOVITCH_LOGIN_RATE_PER_MINUTE", "")
    assert login_rate_limit_per_minute() is None


def test_hsts_max_age_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IPOVITCH_HSTS_MAX_AGE", raising=False)
    assert hsts_max_age_seconds() is None
    monkeypatch.setenv("IPOVITCH_HSTS_MAX_AGE", "31536000")
    assert hsts_max_age_seconds() == 31536000
    monkeypatch.setenv("IPOVITCH_HSTS_MAX_AGE", "0")
    assert hsts_max_age_seconds() is None
    monkeypatch.setenv("IPOVITCH_HSTS_MAX_AGE", "nope")
    assert hsts_max_age_seconds() is None


def test_hsts_header_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_HSTS_MAX_AGE", "60")
    client = TestClient(create_app())
    r = client.get("/health")
    assert "max-age=60" in r.headers.get("Strict-Transport-Security", "")


def test_permissions_policy_on_response(client: TestClient) -> None:
    r = client.get("/health")
    assert r.headers.get("Permissions-Policy")
    assert "camera=()" in r.headers["Permissions-Policy"]


def test_cache_control_no_store_on_v1(client: TestClient) -> None:
    xml = Path(__file__).parent / "fixtures" / "minimal.xml"
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", xml.read_bytes(), "application/xml")},
    )
    assert r.headers.get("Cache-Control", "").startswith("no-store")


def test_cache_control_on_openapi_json(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(create_app())
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "no-store" in r.headers.get("Cache-Control", "")


def test_post_auth_token_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD", "pw")
    monkeypatch.setenv("IPOVITCH_LOGIN_RATE_PER_MINUTE", "3")
    client = TestClient(create_app())
    for _ in range(3):
        assert client.post("/v1/auth/token", json={"password": "bad"}).status_code == 401
    assert client.post("/v1/auth/token", json={"password": "bad"}).status_code == 429


def test_login_rate_disabled_no_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD", "pw")
    monkeypatch.setenv("IPOVITCH_LOGIN_RATE_PER_MINUTE", "0")
    client = TestClient(create_app())
    for _ in range(5):
        assert client.post("/v1/auth/token", json={"password": "bad"}).status_code == 401


def test_max_body_middleware_rejects_by_content_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """httpx may omit Content-Length on large bodies; test the middleware directly."""
    monkeypatch.setattr("app.config.max_upload_bytes", lambda: 100)

    async def _endpoint(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/t", _endpoint, methods=["POST"])])
    app.add_middleware(MaxBodySizeMiddleware)
    c = TestClient(app)
    r = c.post("/t", headers={"Content-Length": "2000000"})
    assert r.status_code == 413
    assert r.json().get("code") == "PAYLOAD_TOO_LARGE"


def test_max_body_invalid_content_length_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.config.max_upload_bytes", lambda: 100)
    client = TestClient(create_app())
    r = client.post(
        "/v1/graph/validate",
        headers={
            "Content-Length": "not-a-number",
            "Content-Type": "application/json",
        },
        content='{"schemaVersion":1,"nodes":[],"edges":[]}',
    )
    assert r.status_code == 200


def test_auth_login_limiter_window_expires() -> None:
    rl = AuthLoginRateLimiter(2, window_seconds=0.06)
    assert rl.allow("ip")
    assert rl.allow("ip")
    assert not rl.allow("ip")
    time.sleep(0.07)
    assert rl.allow("ip")


def test_enforce_login_rate_unknown_client_ip() -> None:
    app = MagicMock()
    app.state.auth_login_rl = AuthLoginRateLimiter(1)
    request = MagicMock()
    request.app = app
    request.client = None

    async def twice() -> None:
        await enforce_login_rate_limit(request)
        await enforce_login_rate_limit(request)

    with pytest.raises(HTTPException) as ei:
        asyncio.run(twice())
    assert ei.value.status_code == 429


def test_jwt_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD", "pw")
    xml = Path(__file__).parent / "fixtures" / "minimal.xml"
    token = pyjwt.encode(
        {
            "sub": "ipovtich",
            "iat": 1,
            "exp": 9_999_999_999,
            "typ": "access",
            "iss": JWT_ISSUER,
            "aud": "other-audience",
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    client = TestClient(create_app())
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", xml.read_bytes(), "application/xml")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
