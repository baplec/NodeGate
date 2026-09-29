import base64
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

from app import service
from app.dependencies import ServerSourceDep, SessionDep, SettingsDep, require_api_key
from app.models import Assignment
from app.schemas import NodeSummary, VpnConfig

router = APIRouter(prefix="/nodes", tags=["nodes"], dependencies=[Depends(require_api_key)])

NodeId = Annotated[
    str,
    Path(pattern=r"^[A-Za-z0-9_.-]{1,64}$", description="Any name for the client, e.g. `node-1` or `42`"),
]
Country = Annotated[
    str | None,
    Query(pattern=r"^[A-Za-z]{2}$", description="Only pick servers in this country (two-letter code, e.g. `JP`)"),
]


def _get_or_404(session: SessionDep, node_id: str) -> Assignment:
    assignment = service.get_assignment(session, node_id)
    if not assignment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Node {node_id!r} has no VPN config")
    return assignment


@router.get("", response_model=list[NodeSummary], summary="List nodes and their servers")
def list_nodes(session: SessionDep):
    return service.list_assignments(session)


@router.post(
    "/{node_id}/config",
    response_model=VpnConfig,
    summary="Get a config, assigning a server if the node has none",
    responses={201: {"description": "A server was assigned"}, 200: {"description": "The node already had a server"}},
)
def assign_config(
    node_id: NodeId,
    response: Response,
    session: SessionDep,
    source: ServerSourceDep,
    settings: SettingsDep,
    country: Country = None,
):
    assignment, created = service.assign(session, source, settings, node_id, country)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return assignment


@router.get("/{node_id}/config", response_model=VpnConfig, summary="Get the node's current config")
def get_config(node_id: NodeId, session: SessionDep):
    return _get_or_404(session, node_id)


@router.get(
    "/{node_id}/config.ovpn",
    response_class=Response,
    summary="Download the node's current config as an .ovpn file",
    responses={200: {"content": {"application/x-openvpn-profile": {}}}},
)
def download_config(node_id: NodeId, session: SessionDep):
    assignment = _get_or_404(session, node_id)
    return Response(
        content=base64.b64decode(assignment.openvpn_config_base64),
        media_type="application/x-openvpn-profile",
        headers={"Content-Disposition": f'attachment; filename="{node_id}.ovpn"'},
    )


@router.post("/{node_id}/config/renew", response_model=VpnConfig, summary="Move the node to a different server")
def renew_config(
    node_id: NodeId,
    session: SessionDep,
    source: ServerSourceDep,
    settings: SettingsDep,
    country: Country = None,
):
    return service.renew(session, source, settings, node_id, country)


@router.delete("/{node_id}/config", status_code=status.HTTP_204_NO_CONTENT, summary="Release the node's server")
def delete_config(node_id: NodeId, session: SessionDep):
    if not service.release(session, node_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Node {node_id!r} has no VPN config")
