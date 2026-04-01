from pathlib import Path

import bcrypt
import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from app.auth_jwt import JWT_AUDIENCE, JWT_ISSUER
from app.config import jwt_ttl_seconds, validate_auth_env
from app.main import create_app

FIXTURE_XML = Path(__file__).parent / "fixtures" / "minimal.xml"

JWT_SECRET = "a" * 32


def test_validate_auth_password_without_jwt_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD", "x")
    monkeypatch.delenv("IPOVITCH_JWT_SECRET", raising=False)
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD_HASH", raising=False)
    with pytest.raises(ValueError, match="IPOVITCH_JWT_SECRET"):
        validate_auth_env()


def test_validate_auth_jwt_without_password_raises_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", JWT_SECRET)
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD", raising=False)
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD_HASH", raising=False)
    with pytest.raises(ValueError, match="IPOVITCH_LOGIN_PASSWORD"):
        validate_auth_env()


def test_validate_auth_jwt_too_short_with_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", "short")
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD", "pw")
    with pytest.raises(ValueError, match="32"):
        validate_auth_env()


def test_auth_status_default_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IPOVITCH_JWT_SECRET", raising=False)
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD", raising=False)
    monkeypatch.delenv("IPOVITCH_API_KEY", raising=False)
    client = TestClient(create_app())
    r = client.get("/v1/auth/status")
    assert r.status_code == 200
    assert r.json() == {"token_login": False, "requires_auth": False}


def test_auth_token_disabled_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IPOVITCH_JWT_SECRET", raising=False)
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD", raising=False)
    client = TestClient(create_app())
    r = client.post("/v1/auth/token", json={"password": "x"})
    assert r.status_code == 404


def test_jwt_login_and_call_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD", "correct-password")
    client = TestClient(create_app())
    bad = client.post("/v1/auth/token", json={"password": "wrong"})
    assert bad.status_code == 401
    ok = client.post("/v1/auth/token", json={"password": "correct-password"})
    assert ok.status_code == 200
    data = ok.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["expires_in"] > 0
    token = data["access_token"]
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


def test_jwt_only_auth_rejects_wrong_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD", "pw")
    client = TestClient(create_app())
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert r.status_code == 401


def test_expired_jwt_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD", "pw")
    client = TestClient(create_app())
    token = pyjwt.encode(
        {
            "sub": "ipovtich",
            "iat": 1,
            "exp": 2,
            "typ": "access",
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


def test_jwt_and_api_key_accepts_either(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD", "pw")
    monkeypatch.setenv("IPOVITCH_API_KEY", "static-key")
    client = TestClient(create_app())
    tok = client.post("/v1/auth/token", json={"password": "pw"}).json()["access_token"]
    r_jwt = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r_jwt.status_code == 200
    r_key = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
        headers={"Authorization": "Bearer static-key"},
    )
    assert r_key.status_code == 200


def test_login_with_bcrypt_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    pw = b"secret-ui-password"
    h = bcrypt.hashpw(pw, bcrypt.gensalt(rounds=4)).decode("ascii")
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD_HASH", h)
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD", raising=False)
    client = TestClient(create_app())
    assert client.post("/v1/auth/token", json={"password": "wrong"}).status_code == 401
    ok = client.post("/v1/auth/token", json={"password": "secret-ui-password"})
    assert ok.status_code == 200


def test_jwt_ttl_seconds_clamp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_TTL_SECONDS", "30")
    assert jwt_ttl_seconds() == 60
    monkeypatch.setenv("IPOVITCH_JWT_TTL_SECONDS", str(86400 * 30))
    assert jwt_ttl_seconds() == 86400 * 7
    monkeypatch.setenv("IPOVITCH_JWT_TTL_SECONDS", "not-int")
    assert jwt_ttl_seconds() == 8 * 3600


def test_auth_password_hash_invalid_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_LOGIN_PASSWORD_HASH", "not-valid-bcrypt")
    from app.auth_password import verify_login_password

    assert verify_login_password("x") is False


def test_verify_login_no_password_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD", raising=False)
    from app.auth_password import verify_login_password

    assert verify_login_password("x") is False


def test_jwt_secret_rejects_short_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPOVITCH_JWT_SECRET", "short")
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD", raising=False)
    monkeypatch.delenv("IPOVITCH_LOGIN_PASSWORD_HASH", raising=False)
    from app.config import jwt_secret

    with pytest.raises(ValueError, match="32"):
        jwt_secret()
