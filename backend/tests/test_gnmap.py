from app.parsers import gnmap


def test_gnmap_parses_host_lines() -> None:
    text = "Host: 10.0.0.1 (gw)\nHost: 10.0.0.2 ()\n"
    g = gnmap.parse_gnmap(text.encode("utf-8"))
    assert len(g.nodes) == 2
    by_id = {n.id: n for n in g.nodes}
    assert by_id["10.0.0.1"].data.label == "gw"
    assert by_id["10.0.0.2"].data.label == "10.0.0.2"
