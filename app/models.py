from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    # Stored as naive UTC so values read back from SQLite match freshly created ones.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Assignment(Base):
    """A VPN server handed out to a node.

    A node has at most one server (node_id is the primary key) and a server
    is never shared between nodes (ip is unique).
    """

    __tablename__ = "assignments"

    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255))
    ip: Mapped[str] = mapped_column(String(45), unique=True)
    country_long: Mapped[str] = mapped_column(String(100))
    country_short: Mapped[str] = mapped_column(String(2))
    openvpn_config_base64: Mapped[str] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
