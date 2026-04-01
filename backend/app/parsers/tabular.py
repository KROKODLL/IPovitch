import csv
import io
import json
from typing import Any

from app.domain.models import NetworkEdge, NetworkGraph, NetworkNode, NodeData, TabularMapping


def _norm_key(row: dict[str, Any], key: str) -> str | None:
    if key in row:
        v = row[key]
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None
    lower_map = {k.lower(): k for k in row}
    lk = key.lower()
    if lk in lower_map:
        v = row[lower_map[lk]]
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None
    return None


def _rows_from_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("TABULAR_CSV_NO_HEADER")
    rows: list[dict[str, str]] = []
    for row in reader:
        rows.append({k: (v or "").strip() for k, v in row.items() if k is not None})
    return rows


def _rows_from_json(content: bytes) -> list[dict[str, Any]]:
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError("TABULAR_JSON_INVALID") from e
    if isinstance(data, list):
        out: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                out.append(item)
        return out
    if isinstance(data, dict):
        inner = data.get("rows") or data.get("data")
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
    raise ValueError("TABULAR_JSON_SHAPE")


def parse_tabular(content: bytes, mapping: TabularMapping) -> NetworkGraph:
    stripped = content.lstrip()
    if stripped.startswith((b"{", b"[")):
        rows = _rows_from_json(content)
    else:
        rows = _rows_from_csv(content)
    if not rows:
        raise ValueError("TABULAR_EMPTY")
    nodes: dict[str, NetworkNode] = {}
    edges: list[NetworkEdge] = []

    def ensure_node(node_id: str) -> None:
        if node_id in nodes:
            return
        data = NodeData(label=node_id, ip=node_id, ports=[], services=None)
        nodes[node_id] = NetworkNode(id=node_id, type="unknown", data=data)

    for i, row in enumerate(rows):
        src = _norm_key(row, mapping.source_key)
        tgt = _norm_key(row, mapping.target_key)
        if src is None or tgt is None:
            raise ValueError("TABULAR_ROW_MISSING_FIELDS")
        ensure_node(src)
        ensure_node(tgt)
        lbl = None
        if mapping.label_key:
            lbl = _norm_key(row, mapping.label_key)
        edges.append(
            NetworkEdge(
                id=f"e-{i}",
                source=src,
                target=tgt,
                label=lbl,
            )
        )
    return NetworkGraph(nodes=list(nodes.values()), edges=edges)
