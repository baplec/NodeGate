import csv
import io
import logging
import threading
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VpnServer:
    hostname: str
    ip: str
    country_long: str
    country_short: str
    score: int
    speed_bps: int
    uptime_ms: int
    openvpn_config_base64: str


class ServerSource(Protocol):
    def get_servers(self) -> list[VpnServer]: ...


class ServerSourceError(Exception):
    """The server list could not be downloaded or read."""


def parse_server_list(text: str) -> list[VpnServer]:
    """Parse the VPN Gate CSV.

    The payload is a "*vpn_servers" line, a header line starting with
    "#HostName", one row per server, then a line containing only "*".
    """
    header_start = text.find("#HostName")
    if header_start == -1:
        raise ServerSourceError("VPN Gate response has no #HostName header")

    servers = []
    for row in csv.DictReader(io.StringIO(text[header_start + 1 :])):
        if row["HostName"].startswith("*"):
            break
        try:
            server = VpnServer(
                hostname=row["HostName"],
                ip=row["IP"],
                country_long=row["CountryLong"],
                country_short=row["CountryShort"],
                score=int(row["Score"]),
                speed_bps=int(row["Speed"]),
                uptime_ms=int(row["Uptime"]),
                openvpn_config_base64=row["OpenVPN_ConfigData_Base64"],
            )
        except (KeyError, TypeError, ValueError):
            logger.debug("Skipping malformed VPN Gate row: %r", row)
            continue
        if server.ip and server.openvpn_config_base64:
            servers.append(server)
    return servers


class VpnGateClient:
    """Downloads the VPN Gate server list and reuses it for `ttl_seconds`.

    If a refresh fails, the previous list keeps being served so a VPN Gate
    outage doesn't take the API down with it.
    """

    def __init__(self, url: str, timeout_seconds: float, ttl_seconds: int):
        self._url = url
        self._timeout = timeout_seconds
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._servers: list[VpnServer] = []
        self._fetched_at = 0.0

    def get_servers(self) -> list[VpnServer]:
        with self._lock:
            if self._servers and time.monotonic() - self._fetched_at < self._ttl:
                return self._servers
            try:
                self._servers = self._fetch()
                self._fetched_at = time.monotonic()
            except ServerSourceError:
                if not self._servers:
                    raise
                logger.warning("VPN Gate refresh failed, serving the cached list", exc_info=True)
            return self._servers

    def _fetch(self) -> list[VpnServer]:
        try:
            response = httpx.get(self._url, timeout=self._timeout, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ServerSourceError(f"Could not download the VPN Gate server list: {exc}") from exc
        servers = parse_server_list(response.text)
        logger.info("Fetched %d servers from VPN Gate", len(servers))
        return servers
