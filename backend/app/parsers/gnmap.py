from app.domain.models import NetworkGraph, NetworkNode, NodeData


def parse_gnmap(content: bytes) -> NetworkGraph:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("GNMAP_DECODE_ERROR") from e
    nodes: dict[str, NetworkNode] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("Host:"):
            continue
        rest = line[5:].strip()
        if not rest:
            continue
        ip = ""
        label = ""
        if "(" in rest and rest.endswith(")"):
            ip_part, _, name_part = rest.partition("(")
            ip = ip_part.strip()
            label = name_part[:-1].strip()
        else:
            ip = rest.split()[0] if rest.split() else ""
            label = ip
        if not ip:
            continue
        if not label:
            label = ip
        if ip in nodes:
            continue
        data = NodeData(label=label, ip=ip, ports=[], services=None)
        nodes[ip] = NetworkNode(id=ip, type="host", data=data)
    if not nodes:
        raise ValueError("GNMAP_NO_HOSTS")
    return NetworkGraph(nodes=list(nodes.values()), edges=[])
