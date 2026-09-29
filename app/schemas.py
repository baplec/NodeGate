from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NodeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_id: str
    hostname: str
    ip: str
    country_long: str
    country_short: str
    assigned_at: datetime


class VpnConfig(NodeSummary):
    openvpn_config_base64: str
