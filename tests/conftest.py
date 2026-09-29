import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.vpngate import ServerSourceError, VpnServer

API_KEY = "test-key"


def make_server(ip: str, country: str = "JP", score: int = 100, speed_bps: int = 100_000_000,
                uptime_ms: int = 700_000_000) -> VpnServer:
    return VpnServer(
        hostname=f"vpn-{ip}",
        ip=ip,
        country_long={"JP": "Japan", "KR": "Korea Republic of"}.get(country, country),
        country_short=country,
        score=score,
        speed_bps=speed_bps,
        uptime_ms=uptime_ms,
        # base64 of "client\n"
        openvpn_config_base64="Y2xpZW50Cg==",
    )


class FakeSource:
    def __init__(self, servers: list[VpnServer]):
        self.servers = servers
        self.fail = False

    def get_servers(self) -> list[VpnServer]:
        if self.fail:
            raise ServerSourceError("VPN Gate is down")
        return self.servers


@pytest.fixture
def source() -> FakeSource:
    return FakeSource([
        make_server("10.0.0.1", "JP", score=300),
        make_server("10.0.0.2", "JP", score=200),
        make_server("10.0.0.3", "KR", score=100),
        make_server("10.0.0.4", "JP", score=999, speed_bps=1_000_000),  # too slow
        make_server("10.0.0.5", "JP", score=999, uptime_ms=1_000),  # too new
    ])


@pytest.fixture
def client(tmp_path, source) -> TestClient:
    settings = Settings(_env_file=None, api_key=API_KEY, database_url=f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(create_app(settings, source), headers={"X-API-Key": API_KEY}) as client:
        yield client
