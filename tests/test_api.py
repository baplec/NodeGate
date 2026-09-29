def test_health_needs_no_key(client):
    response = client.get("/health", headers={"X-API-Key": ""})
    assert response.status_code == 200


def test_missing_or_wrong_key_is_rejected(client):
    assert client.get("/nodes", headers={"X-API-Key": ""}).status_code == 401
    assert client.get("/nodes", headers={"X-API-Key": "nope"}).status_code == 401


def test_assign_picks_best_eligible_server(client):
    response = client.post("/nodes/node-1/config")
    assert response.status_code == 201
    body = response.json()
    assert body["node_id"] == "node-1"
    assert body["ip"] == "10.0.0.1"  # highest score that passes the speed/uptime filters
    assert body["openvpn_config_base64"] == "Y2xpZW50Cg=="


def test_assign_is_idempotent(client):
    first = client.post("/nodes/node-1/config").json()
    second = client.post("/nodes/node-1/config")
    assert second.status_code == 200
    assert second.json()["ip"] == first["ip"]
    assert len(client.get("/nodes").json()) == 1


def test_nodes_never_share_a_server(client):
    ips = {client.post(f"/nodes/node-{i}/config").json()["ip"] for i in range(3)}
    assert ips == {"10.0.0.1", "10.0.0.2", "10.0.0.3"}


def test_no_free_server_returns_503(client):
    for i in range(3):
        client.post(f"/nodes/node-{i}/config")
    response = client.post("/nodes/node-3/config")
    assert response.status_code == 503
    assert client.get("/nodes/node-3/config").status_code == 404


def test_country_filter(client):
    response = client.post("/nodes/node-1/config", params={"country": "kr"})
    assert response.json()["ip"] == "10.0.0.3"
    assert client.post("/nodes/node-2/config", params={"country": "US"}).status_code == 503
    assert client.post("/nodes/node-2/config", params={"country": "USA"}).status_code == 422


def test_get_config(client):
    assert client.get("/nodes/node-1/config").status_code == 404
    client.post("/nodes/node-1/config")
    assert client.get("/nodes/node-1/config").json()["ip"] == "10.0.0.1"


def test_download_ovpn(client):
    client.post("/nodes/node-1/config")
    response = client.get("/nodes/node-1/config.ovpn")
    assert response.status_code == 200
    assert response.content == b"client\n"
    assert response.headers["content-type"] == "application/x-openvpn-profile"
    assert 'filename="node-1.ovpn"' in response.headers["content-disposition"]


def test_renew_moves_node_to_another_server(client):
    client.post("/nodes/node-1/config")
    response = client.post("/nodes/node-1/config/renew")
    assert response.status_code == 200
    assert response.json()["ip"] == "10.0.0.2"
    assert client.get("/nodes/node-1/config").json()["ip"] == "10.0.0.2"


def test_renew_without_free_server_keeps_current(client):
    for i in range(3):
        client.post(f"/nodes/node-{i}/config")
    assert client.post("/nodes/node-0/config/renew").status_code == 503
    assert client.get("/nodes/node-0/config").json()["ip"] == "10.0.0.1"


def test_renew_assigns_when_node_has_none(client):
    response = client.post("/nodes/node-1/config/renew")
    assert response.status_code == 200
    assert response.json()["ip"] == "10.0.0.1"


def test_delete_frees_the_server(client):
    client.post("/nodes/node-1/config")
    assert client.delete("/nodes/node-1/config").status_code == 204
    assert client.delete("/nodes/node-1/config").status_code == 404
    assert client.post("/nodes/node-2/config").json()["ip"] == "10.0.0.1"


def test_invalid_node_id_is_rejected(client):
    assert client.post("/nodes/bad%20id/config").status_code == 422


def test_upstream_failure_returns_502(client, source):
    source.fail = True
    assert client.post("/nodes/node-1/config").status_code == 502
