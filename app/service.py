from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Assignment, utcnow
from app.vpngate import ServerSource, VpnServer


class NoServerAvailable(Exception):
    """Every server that passes the filters is already assigned."""


def eligible_servers(
    servers: list[VpnServer],
    settings: Settings,
    country: str | None = None,
    exclude_ips: Collection[str] = (),
) -> list[VpnServer]:
    """Servers that are fast, stable, free and in the requested country, best score first."""
    candidates = [
        s
        for s in servers
        if s.speed_bps >= settings.min_speed_bps
        and s.uptime_ms >= settings.min_uptime_ms
        and s.ip not in exclude_ips
        and (country is None or s.country_short.upper() == country.upper())
    ]
    return sorted(candidates, key=lambda s: s.score, reverse=True)


def list_assignments(session: Session) -> list[Assignment]:
    return list(session.scalars(select(Assignment).order_by(Assignment.node_id)))


def get_assignment(session: Session, node_id: str) -> Assignment | None:
    return session.get(Assignment, node_id)


def assign(
    session: Session, source: ServerSource, settings: Settings, node_id: str, country: str | None = None
) -> tuple[Assignment, bool]:
    """Return the node's server, assigning one first if it has none.

    The second value is True when a new server was assigned.
    """
    existing = session.get(Assignment, node_id)
    if existing:
        return existing, False
    return _assign_free_server(session, source, settings, node_id, country), True


def renew(
    session: Session, source: ServerSource, settings: Settings, node_id: str, country: str | None = None
) -> Assignment:
    """Move the node to a different server (or assign one if it has none).

    If no other server is free, the node keeps its current one and
    NoServerAvailable is raised.
    """
    return _assign_free_server(session, source, settings, node_id, country)


def release(session: Session, node_id: str) -> bool:
    assignment = session.get(Assignment, node_id)
    if not assignment:
        return False
    session.delete(assignment)
    session.commit()
    return True


def _assign_free_server(
    session: Session, source: ServerSource, settings: Settings, node_id: str, country: str | None
) -> Assignment:
    # Includes the node's own current server, so a renewal always moves it.
    taken_ips = set(session.scalars(select(Assignment.ip)))
    for server in eligible_servers(source.get_servers(), settings, country, taken_ips):
        assignment = _save(session, node_id, server)
        if assignment:
            return assignment
    raise NoServerAvailable()


def _save(session: Session, node_id: str, server: VpnServer) -> Assignment | None:
    """Point the node at `server`. Returns None if another request took that server first."""
    assignment = session.get(Assignment, node_id) or Assignment(node_id=node_id)
    assignment.hostname = server.hostname
    assignment.ip = server.ip
    assignment.country_long = server.country_long
    assignment.country_short = server.country_short
    assignment.openvpn_config_base64 = server.openvpn_config_base64
    assignment.assigned_at = utcnow()
    session.add(assignment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return None
    return assignment
