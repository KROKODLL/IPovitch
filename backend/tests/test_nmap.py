from pathlib import Path

import pytest

from app.parsers import nmap_xml

FIXTURE = Path(__file__).parent / "fixtures" / "minimal.xml"


def test_nmap_preserves_open_ports() -> None:
    raw = FIXTURE.read_bytes()
    graph = nmap_xml.parse_nmap_xml(raw)
    assert len(graph.nodes) == 1
    node = graph.nodes[0]
    assert node.data.ip == "10.0.0.5"
    assert set(node.data.ports) == {22, 443}
    assert "ssh" in (node.data.services or [])


def test_nmap_invalid_xml() -> None:
    with pytest.raises(ValueError, match="NMAP_XML_INVALID"):
        nmap_xml.parse_nmap_xml(b"not xml")
