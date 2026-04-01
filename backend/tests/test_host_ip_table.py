from pathlib import Path

import pytest

from app.parsers import host_ip_table

FIXTURE = Path(__file__).parent / "fixtures" / "host_ip_paste.txt"


def test_host_ip_table_skips_noise_and_builds_edges() -> None:
    raw = FIXTURE.read_bytes()
    graph = host_ip_table.parse_host_ip_table(raw)
    ids = {n.id for n in graph.nodes}
    assert "svc-a.inventory.test" in ids
    assert "192.0.2.10" in ids
    assert "www.inventory.test" in ids
    assert "198.51.100.20" in ids
    na = next(n for n in graph.nodes if n.id == "svc-pending.inventory.test")
    assert na.data.ip == "N/A"
    assert sum(1 for e in graph.edges if e.target == "192.0.2.10") == 2


def test_host_ip_table_space_separated() -> None:
    graph = host_ip_table.parse_host_ip_table(b"host.alpha.test 192.0.2.1\n")
    assert len(graph.nodes) == 2
    assert any(e.source == "host.alpha.test" and e.target == "192.0.2.1" for e in graph.edges)


def test_host_ip_table_empty_raises() -> None:
    with pytest.raises(ValueError, match="HOST_IP_NO_ROWS"):
        host_ip_table.parse_host_ip_table(b"Subdomain\nSort by\n")


def test_host_ip_bulk_inventory_block() -> None:
    block = """Subdomain
in ascending order
Sort by
IP Address
in ascending order
svc-a.inventory.test	192.0.2.10
svc-b.inventory.test	192.0.2.10
svc-c.inventory.test	192.0.2.10
www.inventory.test	198.51.100.20
svc-docs.inventory.test	203.0.113.11
svc-qa.inventory.test	203.0.113.11
svc-pending-a.inventory.test	N/A
svc-pending-b.inventory.test	N/A
"""
    graph = host_ip_table.parse_host_ip_table(block.encode("utf-8"))
    assert len(graph.edges) >= 6
    na = next(n for n in graph.nodes if n.id == "svc-pending-a.inventory.test")
    assert na.data.ip == "N/A"


def test_host_ip_nbsp_between_columns() -> None:
    raw = "host.alpha.test\u00a0192.0.2.2\n".encode()
    graph = host_ip_table.parse_host_ip_table(raw)
    assert any(n.id == "host.alpha.test" for n in graph.nodes)
    assert any(e.target == "192.0.2.2" for e in graph.edges)


def test_host_ip_ip_first_column() -> None:
    raw = b"192.0.2.5\tserver.internal.corp\n"
    graph = host_ip_table.parse_host_ip_table(raw)
    assert any(n.id == "server.internal.corp" for n in graph.nodes)
    assert any(e.source == "server.internal.corp" and e.target == "192.0.2.5" for e in graph.edges)


def test_host_ip_comma_separated() -> None:
    graph = host_ip_table.parse_host_ip_table(b"host.inventory.test,192.0.2.3\n")
    assert any(e.target == "192.0.2.3" for e in graph.edges)


def test_host_ip_invalid_hostname_line_skipped() -> None:
    raw = b"not a valid host 192.0.2.4\nhost.ok.inventory.test\t192.0.2.5\n"
    graph = host_ip_table.parse_host_ip_table(raw)
    assert not any(n.id == "not a valid host" for n in graph.nodes)
    assert any(n.id == "host.ok.inventory.test" for n in graph.nodes)


def test_host_ip_tab_single_column_skipped() -> None:
    graph = host_ip_table.parse_host_ip_table(b"onlyone\nhost.ok\t192.0.2.6\n")
    assert any(n.id == "host.ok" for n in graph.nodes)


def test_host_ip_comma_empty_part_skipped() -> None:
    graph = host_ip_table.parse_host_ip_table(b",\nhost.ok\t192.0.2.7\n")
    assert any(n.id == "host.ok" for n in graph.nodes)


def test_host_ip_short_label_fullmatch() -> None:
    graph = host_ip_table.parse_host_ip_table(b"ab\t192.0.2.20\n")
    assert len(graph.edges) == 1


def test_host_ip_single_token_line_skipped() -> None:
    graph = host_ip_table.parse_host_ip_table(b"onlytoken\nhost.ok\t192.0.2.21\n")
    assert any(n.id == "host.ok" for n in graph.nodes)


def test_host_ip_tab_only_one_field_skipped() -> None:
    with pytest.raises(ValueError, match="HOST_IP_NO_ROWS"):
        host_ip_table.parse_host_ip_table(b"\t192.0.2.22\n")


def test_host_ip_hostname_too_long_raises() -> None:
    long_h = "x" * 254
    with pytest.raises(ValueError, match="HOST_IP_NO_ROWS"):
        host_ip_table.parse_host_ip_table(f"{long_h}\t192.0.2.23\n".encode())


def test_host_ip_both_tokens_ip_rejected() -> None:
    with pytest.raises(ValueError, match="HOST_IP_NO_ROWS"):
        host_ip_table.parse_host_ip_table(b"192.0.2.30\t192.0.2.31\n")


def test_host_ip_tab_line_single_column_after_strip() -> None:
    graph = host_ip_table.parse_host_ip_table(b"h\t\nok\t192.0.2.26\n")
    assert any(n.id == "ok" for n in graph.nodes)


def test_host_ip_host_equals_token_rejected() -> None:
    graph = host_ip_table.parse_host_ip_table(b"x\tx\nz\t192.0.2.27\n")
    assert any(n.id == "z" for n in graph.nodes)
    assert not any(n.id == "x" for n in graph.nodes)


def test_split_host_ip_tab_incomplete() -> None:
    assert host_ip_table._split_host_ip("h\t") is None


def test_split_host_ip_duplicate_token() -> None:
    assert host_ip_table._split_host_ip("x\tx") is None
