import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.config import Settings
from app.database import create_db_engine, init_db
from app.routes import router
from app.service import NoServerAvailable
from app.vpngate import ServerSource, ServerSourceError, VpnGateClient

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None, server_source: ServerSource | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
    settings = settings or Settings()
    engine = create_db_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(engine)
        if not settings.api_key:
            logger.warning("API_KEY is not set: the API is open to anyone who can reach it")
        yield
        engine.dispose()

    app = FastAPI(
        title="NodeGate",
        description="Serves OpenVPN configuration files on demand. Each node gets its own server.",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.sessionmaker = sessionmaker(engine, expire_on_commit=False)
    app.state.server_source = server_source or VpnGateClient(
        settings.vpngate_url, settings.vpngate_timeout_seconds, settings.server_list_ttl_seconds
    )

    @app.exception_handler(NoServerAvailable)
    def no_server_available(request: Request, exc: NoServerAvailable) -> JSONResponse:
        return JSONResponse({"detail": "No VPN server available"}, status.HTTP_503_SERVICE_UNAVAILABLE)

    @app.exception_handler(ServerSourceError)
    def server_source_error(request: Request, exc: ServerSourceError) -> JSONResponse:
        logger.error("%s", exc)
        return JSONResponse({"detail": "Could not fetch the VPN server list"}, status.HTTP_502_BAD_GATEWAY)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app
