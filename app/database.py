from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_db_engine(database_url: str) -> Engine:
    connect_args = {}
    if make_url(database_url).get_backend_name() == "sqlite":
        # FastAPI runs sync endpoints in a thread pool.
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    """Create the SQLite folder if needed, then any missing tables."""
    url = engine.url
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
