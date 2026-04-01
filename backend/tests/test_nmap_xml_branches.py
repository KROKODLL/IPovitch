import pytest

from app.parsers import nmap_xml


def test_nmap_ipv6_when_no_ipv4() -> None:
    xml = b"""<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="2001:db8::1" addrtype="ipv6"/>
  </host>
</nmaprun>"""
    g = nmap_xml.parse_nmap_xml(xml)
    assert len(g.nodes) == 1
    assert g.nodes[0].data.ip == "2001:db8::1"


def test_nmap_ipv4_preferred_over_ipv6() -> None:
    xml = b"""<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="192.0.2.1" addrtype="ipv4"/>
    <address addr="2001:db8::2" addrtype="ipv6"/>
  </host>
</nmaprun>"""
    g = nmap_xml.parse_nmap_xml(xml)
    assert g.nodes[0].data.ip == "192.0.2.1"


def test_nmap_wrong_root_tag() -> None:
    with pytest.raises(ValueError, match="NMAP_XML_INVALID"):
        nmap_xml.parse_nmap_xml(b'<?xml version="1.0"?><foo></foo>')


def test_nmap_port_open_without_digit_id_skipped() -> None:
    xml = b"""<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="192.0.2.2" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp">
        <state state="open"/>
      </port>
    </ports>
  </host>
</nmaprun>"""
    g = nmap_xml.parse_nmap_xml(xml)
    assert g.nodes[0].data.ports == []


def test_nmap_port_open_service_without_name() -> None:
    xml = b"""<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="192.0.2.3" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="8080">
        <state state="open"/>
        <service/>
      </port>
    </ports>
  </host>
</nmaprun>"""
    g = nmap_xml.parse_nmap_xml(xml)
    assert g.nodes[0].data.ports == [8080]
    assert g.nodes[0].data.services is None


def test_nmap_os_guess_present() -> None:
    xml = b"""<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="192.0.2.4" addrtype="ipv4"/>
    <os>
      <osmatch name="Linux 5.x"/>
    </os>
  </host>
</nmaprun>"""
    g = nmap_xml.parse_nmap_xml(xml)
    assert g.nodes[0].data.os == "Linux 5.x"


def test_nmap_port_open_missing_state_element_skipped() -> None:
    xml = b"""<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="192.0.2.8" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
      </port>
      <port protocol="tcp" portid="23">
      </port>
    </ports>
  </host>
</nmaprun>"""
    g = nmap_xml.parse_nmap_xml(xml)
    assert g.nodes[0].data.ports == [22]


def test_nmap_host_skipped_without_address() -> None:
    xml = b"""<?xml version="1.0"?>
<nmaprun>
  <host></host>
</nmaprun>"""
    g = nmap_xml.parse_nmap_xml(xml)
    assert g.nodes == []
