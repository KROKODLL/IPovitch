import ipaddress
import re
from typing import Final

from app.domain.models import NetworkEdge, NetworkGraph, NetworkNode, NodeData

_NOISE_LINE: Final[re.Pattern[str]] = re.compile(
    r"^("
    r"subdomain|sort by|ip address|in ascending order|in descending order"
    r")\s*$",
    re.IGNORECASE,
)

_SPACE_LIKE: Final[tuple[str, ...]] = (
    "\ufeff",
    "\u00a0",
    "\u202f",
    "\u2007",
    "\u2009",
    "\u2003",
    "\u2002",
    "\u3000",
)

_NA_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "",
        "-",
        "\u2014",
        "n/a",
        "na",
        "none",
        "null",
        "pending",
        "unknown",
    }
)


def _normalize_line(line: str) -> str:
    s = line.strip().strip("\ufeff")
    for ch in _SPACE_LIKE:
        s = s.replace(ch, " ")
    s = s.rstrip().rstrip('"').rstrip("'").rstrip()
    return s


def _strip_field(s: str) -> str:
    return s.strip().strip('"').strip("'").strip()


def _normalize_ip_token(raw: str) -> str | None:
    s = _strip_field(raw)
    if s.lower() in _NA_TOKENS:
        return None
    try:
        ipaddress.ip_address(s)
    except ValueError:
        return None
    return s


def _looks_like_hostname(s: str) -> bool:
    if len(s) < 1 or len(s) > 253:
        return False
    if _normalize_ip_token(s) is not None:
        return False
    if s.strip() == s and re.fullmatch(r"[\w.\-:]+", s):
        return True
    return any(c in s for c in (".", ":", "-"))


def _split_host_ip(line: str) -> tuple[str, str] | None:
    line = _normalize_line(line)

    host: str | None = None
    ip_tok: str | None = None

    if "\t" in line:
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) >= 2:
            host, ip_tok = parts[0], parts[-1]
    elif "," in line and line.count(",") == 1:
        left, right = line.split(",", 1)
        lh, rh = left.strip(), right.strip()
        if lh and rh:
            host, ip_tok = lh, rh
    else:
        parts = line.rsplit(None, 1)
        if len(parts) == 2:
            host, ip_tok = _strip_field(parts[0]), _strip_field(parts[1])

    if host is None or ip_tok is None:
        return None

    host = _strip_field(host)
    ip_tok = _strip_field(ip_tok)

    if not host or not ip_tok or host == ip_tok:
        return None

    left_ip = _normalize_ip_token(host)
    right_ip = _normalize_ip_token(ip_tok)
    if left_ip is not None and right_ip is None and _looks_like_hostname(ip_tok):
        host, ip_tok = ip_tok, host

    if not _looks_like_hostname(host):
        return None

    return host, ip_tok


def parse_host_ip_table(content: bytes) -> NetworkGraph:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("HOST_IP_INVALID_UTF8") from e
    rows: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = _normalize_line(raw)
        if not line or _NOISE_LINE.match(line):
            continue
        parsed = _split_host_ip(line)
        if parsed is None:
            continue
        host, ip_tok = parsed
        rows.append((host, ip_tok))

    if not rows:
        raise ValueError("HOST_IP_NO_ROWS")

    nodes: dict[str, NetworkNode] = {}
    edges: list[NetworkEdge] = []

    def ensure_ip_node(ip: str) -> None:
        if ip in nodes:
            return
        nodes[ip] = NetworkNode(
            id=ip,
            type="host",
            data=NodeData(label=ip, ip=ip, ports=[], services=None),
        )

    edge_i = 0
    for host, ip_tok in rows:
        resolved = _normalize_ip_token(ip_tok)
        display_ip = resolved if resolved is not None else ip_tok.strip().upper()
        nodes[host] = NetworkNode(
            id=host,
            type="host",
            data=NodeData(label=host, ip=display_ip, ports=[], services=None),
        )
        if resolved is not None:
            ensure_ip_node(resolved)
            edges.append(
                NetworkEdge(
                    id=f"e-{edge_i}",
                    source=host,
                    target=resolved,
                    label=None,
                )
            )
            edge_i += 1

    return NetworkGraph(schemaVersion=1, nodes=list(nodes.values()), edges=edges)
