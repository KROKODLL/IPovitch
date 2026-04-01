from pathlib import Path

import pytest

from app.application import ingest

FIXTURE_XML = Path(__file__).parent / "fixtures" / "minimal.xml"


def test_parse_nmap_xml_by_extension() -> None:
    raw = FIXTURE_XML.read_bytes()
    g = ingest.parse_nmap_file("scan.xml", raw)
    assert len(g.nodes) == 1


def test_parse_nmap_format_from_basename_only() -> None:
    raw = FIXTURE_XML.read_bytes()
    g = ingest.parse_nmap_file("ignored/../../../scan.xml", raw)
    assert len(g.nodes) == 1


def test_parse_nmap_gnmap_by_extension() -> None:
    raw = b"Host: 192.0.2.1 (gw)\n"
    g = ingest.parse_nmap_file("hosts.gnmap", raw)
    assert any(n.id == "192.0.2.1" for n in g.nodes)


def test_parse_nmap_unknown_extension() -> None:
    with pytest.raises(ValueError, match="NMAP_UNKNOWN_FORMAT"):
        ingest.parse_nmap_file("scan.txt", b"<nmaprun></nmaprun>")
