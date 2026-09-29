# NodeGate

A small backend that serves OpenVPN configuration files on demand.

A client (a "node") asks for a config under a name of its choice. NodeGate picks a fast, stable server from the public [VPN Gate](https://www.vpngate.net/) list and gives the node that server's config. It never gives the same server to two nodes. The assignment is stored, so the node gets the same config back until it renews or releases it.

## Run with Docker

```bash
cp .env.example .env
# Set API_KEY in .env, e.g. with:
python -c "import secrets; print(secrets.token_urlsafe(32))"

docker compose up -d --build
```

The API listens on http://localhost:8000. Interactive docs are at http://localhost:8000/docs; use the **Authorize** button to enter your key.

The container won't start without `API_KEY`. The SQLite database is stored in the `nodegate-data` volume, so assignments survive restarts and rebuilds.

```bash
docker compose logs -f     # follow logs
docker compose down        # stop (data is kept)
docker compose down -v     # stop and delete the database
```

## Using the API

Every `/nodes` request needs the `X-API-Key` header. A node name can be 1–64 characters of letters, digits, `.`, `_` and `-`.

| Method   | Path                              | What it does |
|----------|-----------------------------------|--------------|
| `POST`   | `/nodes/{node}/config`            | Returns the node's config, assigning a server first if it has none (`201` when newly assigned, `200` otherwise) |
| `GET`    | `/nodes/{node}/config`            | Returns the node's current config as JSON |
| `GET`    | `/nodes/{node}/config.ovpn`       | Downloads the node's current config as an `.ovpn` file |
| `POST`   | `/nodes/{node}/config/renew`      | Moves the node to a different server (or assigns one if it has none) |
| `DELETE` | `/nodes/{node}/config`            | Releases the node's server |
| `GET`    | `/nodes`                          | Lists all nodes and their servers |
| `GET`    | `/health`                         | Health check, no key needed |

`POST .../config` and `POST .../config/renew` accept `?country=JP` (any two-letter code) to pick only servers in that country. The filter applies when a server is being chosen. If the node already has one, `POST .../config` returns it unchanged, so use `renew` to switch country.

### Example: get a config and connect

```bash
KEY=your-api-key

# Assign a server to "laptop" (or get the one it already has)
curl -X POST -H "X-API-Key: $KEY" "http://localhost:8000/nodes/laptop/config?country=JP"

# Download it and connect
curl -H "X-API-Key: $KEY" -o laptop.ovpn http://localhost:8000/nodes/laptop/config.ovpn
sudo openvpn --config laptop.ovpn
```

The JSON response looks like this:

```json
{
  "node_id": "laptop",
  "hostname": "public-vpn-203",
  "ip": "219.100.37.164",
  "country_long": "Japan",
  "country_short": "JP",
  "assigned_at": "2026-09-29T14:05:27.199208",
  "openvpn_config_base64": "IyMjIyMjIyMj..."
}
```

`assigned_at` is in UTC.

### Errors

Errors use standard status codes and a `detail` message:

| Status | Meaning |
|--------|---------|
| `401`  | Missing or wrong `X-API-Key` |
| `404`  | The node has no config |
| `422`  | Invalid node name or country code |
| `502`  | VPN Gate couldn't be reached and there's no cached list yet |
| `503`  | Every server that passes the filters is already taken. On `renew`, the node keeps its current server. |

## How servers are chosen

The VPN Gate list is downloaded when needed and reused for 5 minutes. If a refresh fails, the last list keeps being used. A server is only handed out if:

- its speed is at least 50 Mbps
- its uptime is at least 7 days
- no other node has it
- it's in the requested country, when `country` is given

Among those, the server with the highest VPN Gate score wins.

## Configuration

Set these in `.env`. Only `API_KEY` is required.

| Variable                  | Default                             | Description |
|---------------------------|-------------------------------------|-------------|
| `API_KEY`                 | none                                | Key clients send in `X-API-Key`. If empty outside Docker, auth is disabled. |
| `PORT`                    | `8000`                              | Host port published by docker compose |
| `DATABASE_URL`            | `sqlite:///./data/nodegate.db`     | SQLAlchemy database URL |
| `VPNGATE_URL`             | `http://www.vpngate.net/api/iphone/`| Server list source |
| `VPNGATE_TIMEOUT_SECONDS` | `30`                                | Timeout for downloading the list |
| `SERVER_LIST_TTL_SECONDS` | `300`                               | How long a downloaded list is reused |
| `MIN_SPEED_BPS`           | `50000000`                          | Minimum server speed, in bits per second |
| `MIN_UPTIME_MS`           | `604800000`                         | Minimum server uptime, in milliseconds |

## Development

Requires Python 3.11+.

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows (source .venv/bin/activate on Linux/macOS)
pip install -r requirements-dev.txt

uvicorn app.main:create_app --factory --reload   # run on http://localhost:8000
pytest                                           # run the tests
```

The tests use a fake server list and a temporary database, so they don't touch VPN Gate.

### Layout

| Path                  | Purpose |
|-----------------------|---------|
| `app/main.py`         | Builds the FastAPI app: settings, database, error handlers |
| `app/routes.py`       | `/nodes` endpoints |
| `app/service.py`      | Server selection and assignment logic |
| `app/vpngate.py`      | Downloads, parses and caches the VPN Gate list |
| `app/models.py`       | `assignments` table |
| `app/schemas.py`      | Response models |
| `app/dependencies.py` | API key check and per-request dependencies |
| `app/config.py`       | Settings from environment variables |
| `tests/`              | pytest suite |

## Notes

- VPN Gate is an academic project, and its servers are run by volunteers. Server quality and availability change constantly, and many operators mark their servers "Academic Use Only".
- The API has one shared key. Put it behind HTTPS (for example with a reverse proxy) before exposing it to the internet.
- Tables are created on startup; there are no migrations yet. If you change `app/models.py`, delete the database (`docker compose down -v`) or add Alembic.
