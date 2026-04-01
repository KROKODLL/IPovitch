from io import BytesIO

import defusedxml.ElementTree as ET

from app.domain.models import NetworkGraph, NetworkNode, NodeData


def _host_addrs(host_el: ET.Element) -> tuple[str | None, list[str]]:
    ipv4: str | None = None
    hostnames: list[str] = []
    for addr in host_el.findall("address"):
        if addr.get("addrtype") == "ipv4":
            ipv4 = addr.get("addr")
        elif addr.get("addrtype") == "ipv6" and ipv4 is None:
            ipv4 = addr.get("addr")
    for hn in host_el.findall("hostnames/hostname"):
        name = hn.get("name")
        if name:
            hostnames.append(name)
    return ipv4, hostnames


def _ports_services(host_el: ET.Element) -> tuple[list[int], list[str]]:
    ports: list[int] = []
    services: list[str] = []
    for port in host_el.findall("ports/port"):
        state = port.find("state")
        if state is None or state.get("state") != "open":
            continue
        portid = port.get("portid")
        if not portid or not portid.isdigit():
            continue
        pnum = int(portid)
        ports.append(pnum)
        svc = port.find("service")
        if svc is not None:
            name = svc.get("name")
            if name:
                services.append(name)
    return ports, services


def _os_guess(host_el: ET.Element) -> str | None:
    os_el = host_el.find("os/osmatch")
    if os_el is None:
        return None
    name = os_el.get("name")
    return name


def parse_nmap_xml(content: bytes) -> NetworkGraph:
    try:
        root = ET.parse(BytesIO(content)).getroot()
    except ET.ParseError as e:
        raise ValueError("NMAP_XML_INVALID") from e
    if root is None or root.tag != "nmaprun":
        raise ValueError("NMAP_XML_INVALID")
    nodes: list[NetworkNode] = []
    for host_el in root.findall("host"):
        ipv4, hostnames = _host_addrs(host_el)
        if not ipv4:
            continue
        ports, services = _ports_services(host_el)
        os_guess = _os_guess(host_el)
        label = hostnames[0] if hostnames else ipv4
        data = NodeData(
            label=label,
            ip=ipv4,
            os=os_guess,
            ports=ports,
            services=services if services else None,
        )
        nodes.append(NetworkNode(id=ipv4, type="host", data=data))
    return NetworkGraph(schemaVersion=1, nodes=nodes, edges=[])
