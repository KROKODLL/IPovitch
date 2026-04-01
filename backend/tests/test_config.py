import pytest

from app.config import (
    CORS_ORIGINS_DEFAULT,
    MAX_UPLOAD_BYTES_DEFAULT,
    MAX_UPLOAD_BYTES_HARD_CAP,
    cors_origins,
    max_upload_bytes,
)


def test_max_upload_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAX_UPLOAD_BYTES", raising=False)
    assert max_upload_bytes() == MAX_UPLOAD_BYTES_DEFAULT


def test_max_upload_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "2048")
    assert max_upload_bytes() == 2048


def test_max_upload_invalid_env_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "not-a-number")
    assert max_upload_bytes() == MAX_UPLOAD_BYTES_DEFAULT


def test_max_upload_whitespace_empty_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "   ")
    assert max_upload_bytes() == MAX_UPLOAD_BYTES_DEFAULT


def test_max_upload_zero_clamped_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "0")
    assert max_upload_bytes() == 1


def test_max_upload_env_clamped_to_hard_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", str(MAX_UPLOAD_BYTES_HARD_CAP + 999))
    assert max_upload_bytes() == MAX_UPLOAD_BYTES_HARD_CAP


def test_cors_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert cors_origins() == list(CORS_ORIGINS_DEFAULT)


def test_cors_custom_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:9000, http://127.0.0.1:9001 , ",
    )
    assert cors_origins() == ["http://127.0.0.1:9000", "http://127.0.0.1:9001"]
