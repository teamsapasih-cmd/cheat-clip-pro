"""Request-scoped database dependencies.

The engine is initialized lazily on the first request that needs persistence.
No connection is opened when the existing application starts.
"""
from __future__ import annotations

from functools import lru_cache
from collections.abc import Iterator

from sqlalchemy.orm import Session

from backend.database.session import build_engine, build_session_factory


@lru_cache(maxsize=1)
def _session_factory():
    return build_session_factory(build_engine())


def get_db_session() -> Iterator[Session]:
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
