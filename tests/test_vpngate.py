import httpx
import pytest

from app import vpngate
from app.vpngate import ServerSourceError, VpnGateClient, parse_server_list

SAMPLE = """*vpn_servers
#HostName,IP,Score,Ping,Speed,CountryLong,CountryShort,NumVpnSessions,Uptime,TotalUsers,TotalTraffic,LogType,Operator,Message,OpenVPN_ConfigData_Base64
public-vpn-1,219.100.37.1,2892441,20,693758421,Japan,JP,75,10967142714,12750330,568665675734929,2weeks,"Operator, Inc.",,Y2xpZW50Cg==
broken,1.2.3.4,notanumber,20,1,Japan,JP,1,1,1,1,2weeks,x,,Y2xpZW50Cg==
no-config,1.2.3.5,1,20,1,Japan,JP,1,1,1,1,2weeks,x,,
*
"""


def test_parse_server_list():
    servers = parse_server_list(SAMPLE)
    assert len(servers) == 1
    server = servers[0]
    assert server.hostname == "public-vpn-1"
    assert server.ip == "219.100.37.1"
    assert server.country_short == "JP"
    assert server.speed_bps == 693758421
    assert server.uptime_ms == 10967142714
    assert server.openvpn_config_base64 == "Y2xpZW50Cg=="


def test_parse_rejects_unexpected_format():
    with pytest.raises(ServerSourceError):
        parse_server_list("<html>maintenance</html>")


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        pass


def test_client_reuses_list_within_ttl(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return FakeResponse(SAMPLE)

    monkeypatch.setattr(vpngate.httpx, "get", fake_get)
    client = VpnGateClient("http://example.test", timeout_seconds=1, ttl_seconds=300)

    client.get_servers()
    client.get_servers()
    assert len(calls) == 1


def test_client_serves_stale_list_when_refresh_fails(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if len(calls) > 1:
            raise httpx.ConnectError("down")
        return FakeResponse(SAMPLE)

    monkeypatch.setattr(vpngate.httpx, "get", fake_get)
    client = VpnGateClient("http://example.test", timeout_seconds=1, ttl_seconds=0)

    assert len(client.get_servers()) == 1
    # TTL of 0 forces a refresh, which fails: the cached list is still returned.
    assert len(client.get_servers()) == 1
    assert len(calls) == 2


def test_client_raises_when_nothing_cached(monkeypatch):
    def fake_get(url, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(vpngate.httpx, "get", fake_get)
    with pytest.raises(ServerSourceError):
        VpnGateClient("http://example.test", timeout_seconds=1, ttl_seconds=300).get_servers()
