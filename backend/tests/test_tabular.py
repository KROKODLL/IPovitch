import json

import pytest

from app.domain.models import TabularMapping
from app.parsers import tabular


def test_csv_edges_match_rows() -> None:
    csv_body = "src,dst,note\na,b,x\nb,c,y\n"
    m = TabularMapping(sourceKey="src", targetKey="dst", labelKey="note")
    g = tabular.parse_tabular(csv_body.encode("utf-8"), m)
    assert len(g.edges) == 2
    assert len(g.nodes) == 3
    assert {e.source for e in g.edges} <= {n.id for n in g.nodes}


def test_json_array_rows() -> None:
    rows = [{"from": "1", "to": "2"}, {"from": "2", "to": "3"}]
    m = TabularMapping(sourceKey="from", targetKey="to")
    g = tabular.parse_tabular(json.dumps(rows).encode("utf-8"), m)
    assert len(g.edges) == 2


def test_missing_field_raises() -> None:
    csv_body = "a,b\n1,\n"
    m = TabularMapping(sourceKey="src", targetKey="dst")
    with pytest.raises(ValueError, match="TABULAR_ROW_MISSING_FIELDS"):
        tabular.parse_tabular(csv_body.encode("utf-8"), m)
