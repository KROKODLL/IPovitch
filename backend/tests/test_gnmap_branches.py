import pytest

from app.parsers import gnmap


def test_gnmap_utf8_decode_error() -> None:
    with pytest.raises(ValueError, match="GNMAP_DECODE_ERROR"):
        gnmap.parse_gnmap(b"\xff\xff")


def test_gnmap_no_hosts_raises() -> None:
    with pytest.raises(ValueError, match="GNMAP_NO_HOSTS"):
        gnmap.parse_gnmap(b"# comment line only\n")


def test_gnmap_skips_non_host_lines() -> None:
    g = gnmap.parse_gnmap(b"Comment: ignored\nHost: 192.0.2.1 ()\n")
    assert len(g.nodes) == 1


def test_gnmap_host_empty_rest_skipped() -> None:
    with pytest.raises(ValueError, match="GNMAP_NO_HOSTS"):
        gnmap.parse_gnmap(b"Host:\n")


def test_gnmap_host_without_paren_parses_ip_only() -> None:
    g = gnmap.parse_gnmap(b"Host: 192.0.2.2 extra tokens\n")
    assert g.nodes[0].data.label == "192.0.2.2"


def test_gnmap_duplicate_ip_ignored() -> None:
    g = gnmap.parse_gnmap(b"Host: 192.0.2.3 (a)\nHost: 192.0.2.3 (b)\n")
    assert len(g.nodes) == 1
    assert g.nodes[0].data.label == "a"


def test_gnmap_empty_label_after_paren_falls_back_ip() -> None:
    g = gnmap.parse_gnmap(b"Host: 192.0.2.4 ()\n")
    assert g.nodes[0].data.label == "192.0.2.4"


def test_gnmap_bom_strip() -> None:
    g = gnmap.parse_gnmap("\ufeffHost: 192.0.2.5 ()\n".encode())
    assert len(g.nodes) == 1


def test_gnmap_host_line_with_empty_ip_skipped() -> None:
    g = gnmap.parse_gnmap(b"Host: ()\nHost: 192.0.2.6 (ok)\n")
    assert len(g.nodes) == 1
    assert g.nodes[0].id == "192.0.2.6"
