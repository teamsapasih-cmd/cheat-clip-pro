"""Database engine/session factory. No engine is created at import time."""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def normalize_database_url(url: str) -> str:
    """Use psycopg 3 explicitly for Supabase/PostgreSQL URLs."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def build_engine(database_url: str | None = None, **kwargs) -> Engine:
    raw_url = database_url or os.environ.get("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("DATABASE_URL is required to create a database engine")
    url = normalize_database_url(raw_url)
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options = {"connect_args": {"check_same_thread": False}}
    elif url.startswith("postgresql+psycopg://"):
        options = {"connect_args": {"prepare_threshold": None}, **options}
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
