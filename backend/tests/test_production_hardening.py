import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.auth_dependency import require_v1_auth
from app.config import CORS_ORIGINS_DEFAULT, cors_origins, openapi_enabled, rate_limit_per_minute
from app.main import create_app

FIXTURE_XML = Path(__file__).parent / "fixtures" / "minimal.xml"


def test_openapi_disabled_hides_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_OPENAPI_ENABLED", "0")
    client = TestClient(create_app())
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_rate_limit_blocks_after_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_RATE_LIMIT_PER_MINUTE", "1")
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 429


def test_api_key_required_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_API_KEY", "secret-key")
    client = TestClient(create_app())
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
    )
    assert r.status_code == 401


def test_api_key_accepts_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_API_KEY", "secret-key")
    client = TestClient(create_app())
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
        headers={"Authorization": "Bearer secret-key"},
    )
    assert r.status_code == 200


def test_api_key_accepts_x_api_key_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_API_KEY", "secret-key")
    client = TestClient(create_app())
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
        headers={"X-Api-Key": "secret-key"},
    )
    assert r.status_code == 200


def test_api_key_rejects_wrong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_API_KEY", "secret-key")
    client = TestClient(create_app())
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401


def test_invalid_cors_origin_star(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValueError, match="Invalid CORS origin"):
        cors_origins()


def test_invalid_cors_origin_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "ftp://example.com")
    with pytest.raises(ValueError, match="Invalid CORS origin"):
        cors_origins()


def test_invalid_cors_empty_netloc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://")
    with pytest.raises(ValueError, match="Invalid CORS origin"):
        cors_origins()


def test_cors_only_commas_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "  , , ")
    assert cors_origins() == list(CORS_ORIGINS_DEFAULT)


def test_rate_limit_per_minute_invalid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_RATE_LIMIT_PER_MINUTE", "not-a-number")
    assert rate_limit_per_minute() is None


def test_rate_limit_per_minute_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_RATE_LIMIT_PER_MINUTE", "0")
    assert rate_limit_per_minute() is None


def test_openapi_enabled_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_OPENAPI_ENABLED", "off")
    assert openapi_enabled() is False
    monkeypatch.setenv("IPOVITCH_OPENAPI_ENABLED", "FALSE")
    assert openapi_enabled() is False


async def _run_require(
    monkeypatch: pytest.MonkeyPatch,
    *,
    authorization: str | None = None,
    x_api_key: str | None = None,
    credentials: HTTPAuthorizationCredentials | None = None,
) -> None:
    monkeypatch.setenv("IPOVITCH_API_KEY", "k")
    await require_v1_auth(
        authorization=authorization,
        x_api_key=x_api_key,
        credentials=credentials,
    )


def test_require_api_key_bearer_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="k")
    asyncio.run(_run_require(monkeypatch, credentials=creds))


def test_require_api_key_x_api_key_only(monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_run_require(monkeypatch, x_api_key="k"))


def test_require_api_key_raw_authorization_header(monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_run_require(monkeypatch, authorization="Bearer k"))


def test_require_api_key_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_API_KEY", "k")

    async def _() -> None:
        await require_v1_auth(authorization=None, x_api_key=None, credentials=None)

    with pytest.raises(HTTPException) as ei:
        asyncio.run(_())
    assert ei.value.status_code == 401


def test_require_api_key_wrong_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_API_KEY", "k")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong")

    async def _() -> None:
        await require_v1_auth(authorization=None, x_api_key=None, credentials=creds)

    with pytest.raises(HTTPException) as ei:
        asyncio.run(_())
    assert ei.value.status_code == 401


def test_require_api_key_unconfigured_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IPOVITCH_API_KEY", raising=False)

    async def _() -> None:
        await require_v1_auth(authorization=None, x_api_key=None, credentials=None)

    asyncio.run(_())
