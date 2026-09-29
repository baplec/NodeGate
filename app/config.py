from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Clients must send this in the X-API-Key header. Leave empty to disable auth (local development only).
    api_key: str | None = None

    database_url: str = "sqlite:///./data/protongen.db"

    vpngate_url: str = "http://www.vpngate.net/api/iphone/"
    vpngate_timeout_seconds: float = 30.0
    # How long a downloaded server list is reused before fetching a new one.
    server_list_ttl_seconds: int = 300

    # Servers slower or younger than this are never handed out.
    min_speed_bps: int = 50_000_000  # 50 Mbps
    min_uptime_ms: int = 604_800_000  # 7 days
