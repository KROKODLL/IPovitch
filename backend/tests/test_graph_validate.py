from unittest.mock import patch

from fastapi.testclient import TestClient


def test_graph_validate_round_trip_empty(client: TestClient) -> None:
    body = {"schemaVersion": 1, "nodes": [], "edges": []}
    r = client.post("/v1/graph/validate", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["schemaVersion"] == 1
    assert data["nodes"] == []
    assert data["edges"] == []
    assert "X-Request-ID" in r.headers


def test_graph_validate_rejects_invalid(client: TestClient) -> None:
    r = client.post("/v1/graph/validate", json={"schemaVersion": 1, "nodes": "bad", "edges": []})
    assert r.status_code == 422
    assert r.json()["code"] == "GRAPH_INVALID"


def test_graph_validate_rejects_malformed_json(client: TestClient) -> None:
    r = client.post(
        "/v1/graph/validate",
        content=b"{",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GRAPH_INVALID"


def test_graph_validate_too_many_nodes(client: TestClient) -> None:
    body = {
        "schemaVersion": 1,
        "nodes": [
            {
                "id": f"n{i}",
                "type": "host",
                "data": {"label": "x", "ip": "192.0.2.1", "ports": []},
            }
            for i in range(3)
        ],
        "edges": [],
    }
    with patch("app.main.GRAPH_VALIDATE_MAX_NODES", 2):
        r = client.post("/v1/graph/validate", json=body)
    assert r.status_code == 422
    assert r.json()["code"] == "GRAPH_TOO_MANY_NODES"


def test_graph_validate_too_many_edges(client: TestClient) -> None:
    nodes = [
        {"id": "a", "type": "host", "data": {"label": "a", "ip": "192.0.2.1", "ports": []}},
        {"id": "b", "type": "host", "data": {"label": "b", "ip": "192.0.2.2", "ports": []}},
    ]
    edges = [{"id": f"e{i}", "source": "a", "target": "b"} for i in range(4)]
    body = {"schemaVersion": 1, "nodes": nodes, "edges": edges}
    with patch("app.main.GRAPH_VALIDATE_MAX_EDGES", 3):
        r = client.post("/v1/graph/validate", json=body)
    assert r.status_code == 422
    assert r.json()["code"] == "GRAPH_TOO_MANY_EDGES"


def test_graph_validate_rejects_oversized_body(client: TestClient) -> None:
    with patch("app.config.max_upload_bytes", return_value=10):
        r = client.post(
            "/v1/graph/validate",
            content=b'{"schemaVersion":1,"nodes":[],"edges":[]}',
            headers={"Content-Type": "application/json"},
        )
    assert r.status_code == 413
    assert r.json()["code"] == "UPLOAD_TOO_LARGE"


def test_graph_validate_echoes_request_id(client: TestClient) -> None:
    r = client.post(
        "/v1/graph/validate",
        json={"schemaVersion": 1, "nodes": [], "edges": []},
        headers={"X-Request-ID": "custom-req-id"},
    )
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "custom-req-id"
