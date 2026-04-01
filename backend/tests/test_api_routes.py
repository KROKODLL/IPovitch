from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import TABULAR_MAPPING_JSON_MAX_LEN

FIXTURE_XML = Path(__file__).parent / "fixtures" / "minimal.xml"


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert "X-Request-ID" in r.headers


def test_health_echoes_x_request_id(client: TestClient) -> None:
    r = client.get("/health", headers={"X-Request-ID": "probe-123"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "probe-123"


def test_security_headers_on_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"


def test_parse_nmap_ok(client: TestClient) -> None:
    r = client.post(
        "/v1/parse/nmap",
        files={"file": ("n.xml", FIXTURE_XML.read_bytes(), "application/xml")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["schemaVersion"] == 1
    assert len(data["nodes"]) == 1


def test_parse_nmap_gnmap_ok(client: TestClient) -> None:
    body = b"Host: 192.0.2.2 ()\n"
    r = client.post("/v1/parse/nmap", files={"file": ("x.gnmap", body, "text/plain")})
    assert r.status_code == 200
    assert any(n["id"] == "192.0.2.2" for n in r.json()["nodes"])


def test_parse_nmap_upload_too_large(client: TestClient) -> None:
    with patch("app.config.max_upload_bytes", return_value=5):
        r = client.post(
            "/v1/parse/nmap",
            files={"file": ("big.xml", b"123456", "application/xml")},
        )
    assert r.status_code == 413
    assert r.json()["code"] == "UPLOAD_TOO_LARGE"


def test_parse_nmap_invalid(client: TestClient) -> None:
    r = client.post("/v1/parse/nmap", files={"file": ("bad.xml", b"not xml", "application/xml")})
    assert r.status_code == 422
    assert r.json()["code"] == "NMAP_XML_INVALID"


def test_parse_nmap_unknown_format(client: TestClient) -> None:
    r = client.post("/v1/parse/nmap", files={"file": ("x.txt", b"data", "text/plain")})
    assert r.status_code == 422
    assert r.json()["code"] == "NMAP_UNKNOWN_FORMAT"


def test_parse_nmap_valueerror_no_code(client: TestClient) -> None:
    with patch("app.main.ingest.parse_nmap_file", side_effect=ValueError()):
        r = client.post(
            "/v1/parse/nmap",
            files={"file": ("x.xml", b"<nmaprun></nmaprun>", "application/xml")},
        )
    assert r.status_code == 422
    assert r.json()["code"] == "PARSE_ERROR"


def test_parse_host_ip_file_ok(client: TestClient) -> None:
    p = Path(__file__).parent / "fixtures" / "host_ip_paste.txt"
    r = client.post(
        "/v1/parse/host-ip-table",
        files={"file": ("hosts.txt", p.read_bytes(), "text/plain")},
    )
    assert r.status_code == 200
    ids = {n["id"] for n in r.json()["nodes"]}
    assert "svc-a.inventory.test" in ids


def test_parse_host_ip_file_too_large(client: TestClient) -> None:
    with patch("app.config.max_upload_bytes", return_value=3):
        r = client.post(
            "/v1/parse/host-ip-table",
            files={"file": ("t.txt", b"abcd", "text/plain")},
        )
    assert r.status_code == 413


def test_parse_host_ip_file_parse_error(client: TestClient) -> None:
    with patch("app.main.host_ip_table.parse_host_ip_table", side_effect=ValueError("X")):
        r = client.post(
            "/v1/parse/host-ip-table",
            files={"file": ("t.txt", b"a\tb\n", "text/plain")},
        )
    assert r.status_code == 422
    assert r.json()["code"] == "X"


def test_parse_host_ip_file_valueerror_empty_args(client: TestClient) -> None:
    with patch("app.main.host_ip_table.parse_host_ip_table", side_effect=ValueError()):
        r = client.post(
            "/v1/parse/host-ip-table",
            files={"file": ("t.txt", b"a\tb\n", "text/plain")},
        )
    assert r.status_code == 422
    assert r.json()["code"] == "PARSE_ERROR"


def test_parse_host_ip_paste_too_large(client: TestClient) -> None:
    with patch("app.config.max_upload_bytes", return_value=2):
        r = client.post("/v1/parse/host-ip-table-paste", json={"text": "abc"})
    assert r.status_code == 422


def test_parse_host_ip_paste_parse_error(client: TestClient) -> None:
    err = ValueError("HOST_IP_NO_ROWS")
    with patch("app.main.host_ip_table.parse_host_ip_table", side_effect=err):
        r = client.post("/v1/parse/host-ip-table-paste", json={"text": "only-noise\n"})
    assert r.status_code == 422


def test_parse_tabular_ok(client: TestClient) -> None:
    csv_body = b"src,dst\na,b\n"
    mapping = '{"sourceKey":"src","targetKey":"dst"}'
    r = client.post(
        "/v1/parse/tabular",
        data={"mapping": mapping},
        files={"file": ("t.csv", csv_body, "text/csv")},
    )
    assert r.status_code == 200
    assert len(r.json()["edges"]) == 1


def test_parse_tabular_mapping_json_too_large(client: TestClient) -> None:
    mapping = "x" * (TABULAR_MAPPING_JSON_MAX_LEN + 1)
    r = client.post(
        "/v1/parse/tabular",
        data={"mapping": mapping},
        files={"file": ("t.csv", b"a,b\n1,2\n", "text/csv")},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "MAPPING_TOO_LARGE"


def test_parse_tabular_mapping_invalid(client: TestClient) -> None:
    r = client.post(
        "/v1/parse/tabular",
        data={"mapping": "not-json"},
        files={"file": ("t.csv", b"a,b\n1,2\n", "text/csv")},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "MAPPING_INVALID"


def test_parse_tabular_too_large(client: TestClient) -> None:
    with patch("app.config.max_upload_bytes", return_value=2):
        r = client.post(
            "/v1/parse/tabular",
            data={"mapping": '{"sourceKey":"a","targetKey":"b"}'},
            files={"file": ("t.csv", b"xxx", "text/csv")},
        )
    assert r.status_code == 413


def test_parse_tabular_parse_error(client: TestClient) -> None:
    r = client.post(
        "/v1/parse/tabular",
        data={"mapping": '{"sourceKey":"a","targetKey":"b"}'},
        files={"file": ("t.json", b"{not-json", "application/json")},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "TABULAR_JSON_INVALID"


def test_parse_tabular_valueerror_no_args(client: TestClient) -> None:
    with patch("app.main.ingest.parse_tabular_file", side_effect=ValueError()):
        r = client.post(
            "/v1/parse/tabular",
            data={"mapping": '{"sourceKey":"s","targetKey":"t"}'},
            files={"file": ("t.csv", b"s,t\na,b\n", "text/csv")},
        )
    assert r.status_code == 422
    assert r.json()["code"] == "PARSE_ERROR"


def test_parse_host_ip_paste_ok(client: TestClient) -> None:
    r = client.post("/v1/parse/host-ip-table-paste", json={"text": "host.a.test\t192.0.2.1\n"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["nodes"]) == 2
    assert any(e["source"] == "host.a.test" and e["target"] == "192.0.2.1" for e in data["edges"])


def test_parse_host_ip_paste_mixed_tabs_spaces(client: TestClient) -> None:
    text = "host.a.test\t192.0.2.1\nhost.b.test 192.0.2.2\n"
    r = client.post("/v1/parse/host-ip-table-paste", json={"text": text})
    assert r.status_code == 200
    ids = {n["id"] for n in r.json()["nodes"]}
    assert "host.a.test" in ids and "host.b.test" in ids


def test_parse_host_ip_file_invalid_utf8(client: TestClient) -> None:
    r = client.post(
        "/v1/parse/host-ip-table",
        files={"file": ("bad.txt", b"\xff\xfe\x00", "text/plain")},
    )
    assert r.status_code == 422
    assert r.json().get("code") == "HOST_IP_INVALID_UTF8"
