from unittest.mock import patch

from fastapi.testclient import TestClient


def test_unexpected_exception_returns_500_json(client: TestClient) -> None:
    with patch(
        "app.main.host_ip_table.parse_host_ip_table",
        side_effect=RuntimeError("simulated bug"),
    ):
        r = client.post(
            "/v1/parse/host-ip-table",
            files={"file": ("t.txt", b"host\t192.0.2.1\n", "text/plain")},
        )
    assert r.status_code == 500
    data = r.json()
    assert data["code"] == "INTERNAL_ERROR"
    assert "X-Request-ID" in r.headers
