import json
from unittest.mock import patch

from app.http_responses import (
    json_413_upload_limit,
    json_422_value_error,
    reject_if_oversized,
)


def test_json_413_upload_limit() -> None:
    r = json_413_upload_limit(42)
    assert r.status_code == 413
    assert json.loads(r.body) == {"code": "UPLOAD_TOO_LARGE", "detail": "42"}


def test_json_422_value_error_with_code() -> None:
    r = json_422_value_error(ValueError("HOST_IP_NO_ROWS"))
    assert r.status_code == 422
    assert json.loads(r.body)["code"] == "HOST_IP_NO_ROWS"


def test_json_422_value_error_no_args() -> None:
    r = json_422_value_error(ValueError())
    assert r.status_code == 422
    assert json.loads(r.body)["code"] == "PARSE_ERROR"


def test_reject_if_oversized_returns_413() -> None:
    with patch("app.config.max_upload_bytes", return_value=2):
        r = reject_if_oversized(b"abc")
    assert r is not None
    assert r.status_code == 413
    assert json.loads(r.body)["code"] == "UPLOAD_TOO_LARGE"


def test_reject_if_oversized_accepts_within_limit() -> None:
    with patch("app.config.max_upload_bytes", return_value=100):
        assert reject_if_oversized(b"ok") is None
