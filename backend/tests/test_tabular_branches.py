import json

import pytest

from app.domain.models import TabularMapping
from app.parsers import tabular


def test_tabular_csv_no_header_raises() -> None:
    with pytest.raises(ValueError, match="TABULAR_CSV_NO_HEADER"):
        tabular.parse_tabular(b"", TabularMapping(sourceKey="a", targetKey="b"))


def test_tabular_csv_empty_rows_raises() -> None:
    with pytest.raises(ValueError, match="TABULAR_EMPTY"):
        tabular.parse_tabular(b"a,b\n", TabularMapping(sourceKey="a", targetKey="b"))


def test_tabular_json_invalid_raises() -> None:
    with pytest.raises(ValueError, match="TABULAR_JSON_INVALID"):
        tabular.parse_tabular(b"{", TabularMapping(sourceKey="a", targetKey="b"))


def test_tabular_json_wrong_shape_raises() -> None:
    body = b'{"note":"no-rows-here"}'
    m = TabularMapping(sourceKey="a", targetKey="b")
    with pytest.raises(ValueError, match="TABULAR_JSON_SHAPE"):
        tabular.parse_tabular(body, m)


def test_tabular_json_rows_not_a_list_raises() -> None:
    with pytest.raises(ValueError, match="TABULAR_JSON_SHAPE"):
        tabular.parse_tabular(b'{"rows":"bad"}', TabularMapping(sourceKey="a", targetKey="b"))


def test_tabular_json_object_with_rows_key() -> None:
    payload = json.dumps({"rows": [{"s": "1", "t": "2"}]}).encode()
    m = TabularMapping(sourceKey="s", targetKey="t")
    g = tabular.parse_tabular(payload, m)
    assert len(g.edges) == 1


def test_tabular_json_object_with_data_key() -> None:
    payload = json.dumps({"data": [{"s": "x", "t": "y"}]}).encode()
    m = TabularMapping(sourceKey="s", targetKey="t")
    g = tabular.parse_tabular(payload, m)
    assert len(g.edges) == 1


def test_tabular_norm_key_none_value_in_row() -> None:
    rows = [{"src": None, "dst": "b"}]
    m = TabularMapping(sourceKey="src", targetKey="dst")
    with pytest.raises(ValueError, match="TABULAR_ROW_MISSING_FIELDS"):
        tabular.parse_tabular(json.dumps(rows).encode(), m)


def test_tabular_norm_key_explicit_none_vs_missing_lower() -> None:
    rows = [{"SRC": None, "dst": "b"}]
    m = TabularMapping(sourceKey="src", targetKey="dst")
    with pytest.raises(ValueError, match="TABULAR_ROW_MISSING_FIELDS"):
        tabular.parse_tabular(json.dumps(rows).encode(), m)


def test_tabular_norm_key_empty_string() -> None:
    rows = [{"src": "", "dst": "b"}]
    m = TabularMapping(sourceKey="src", targetKey="dst")
    with pytest.raises(ValueError, match="TABULAR_ROW_MISSING_FIELDS"):
        tabular.parse_tabular(json.dumps(rows).encode(), m)


def test_tabular_norm_key_empty_via_alias_key() -> None:
    rows = [{"SRC": "   ", "dst": "b"}]
    m = TabularMapping(sourceKey="src", targetKey="dst")
    with pytest.raises(ValueError, match="TABULAR_ROW_MISSING_FIELDS"):
        tabular.parse_tabular(json.dumps(rows).encode(), m)


def test_tabular_norm_key_case_insensitive() -> None:
    csv_body = "SRC,DST\na,b\n"
    m = TabularMapping(sourceKey="src", targetKey="dst")
    g = tabular.parse_tabular(csv_body.encode(), m)
    assert len(g.edges) == 1


def test_tabular_label_key_optional_used() -> None:
    csv_body = "s,t,l\na,b,edge1\n"
    m = TabularMapping(sourceKey="s", targetKey="t", labelKey="l")
    g = tabular.parse_tabular(csv_body.encode(), m)
    assert g.edges[0].label == "edge1"


def test_tabular_label_key_missing_in_row() -> None:
    csv_body = "s,t\na,b\n"
    m = TabularMapping(sourceKey="s", targetKey="t", labelKey="lbl")
    g = tabular.parse_tabular(csv_body.encode(), m)
    assert g.edges[0].label is None
