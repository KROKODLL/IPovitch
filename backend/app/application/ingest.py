import os

from app.domain.models import NetworkGraph, TabularMapping
from app.parsers import gnmap, nmap_xml, tabular


def parse_nmap_file(filename: str, content: bytes) -> NetworkGraph:
    base = os.path.basename(filename) or "scan.xml"
    lower = base.lower()
    if lower.endswith(".gnmap"):
        return gnmap.parse_gnmap(content)
    if lower.endswith(".xml"):
        return nmap_xml.parse_nmap_xml(content)
    raise ValueError("NMAP_UNKNOWN_FORMAT")


def parse_tabular_file(content: bytes, mapping: TabularMapping) -> NetworkGraph:
    return tabular.parse_tabular(content, mapping)
