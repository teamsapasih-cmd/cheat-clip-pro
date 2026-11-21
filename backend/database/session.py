"""Database engine/session factory. No engine is created at import time."""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def build_engine(database_url: str | None = None, **kwargs) -> Engine:
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required to create a database engine")

    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options = {"connect_args": {"check_same_thread": False}}
    options.update(kwargs)
    return create_engine(url, **options)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session(factory: sessionmaker[Session]) -> Iterator[Session]:
    """FastAPI dependency helper; caller supplies the configured factory."""
    session = factory()
    try:
        yield session
    finally:
        session.close()
