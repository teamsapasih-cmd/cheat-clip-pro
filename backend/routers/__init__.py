"""Lazy router exports to avoid loading video/AI dependencies in lightweight API tests.

Importing one router should not eagerly import every legacy route and its optional
AI/video dependencies. The FastAPI application still receives the same exports.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

_ROUTER_EXPORTS = {
    "analyze_router": ("backend.routers.analyze", "router"),
    "cookies_router": ("backend.routers.cookies", "router"),
    "downloads_router": ("backend.routers.downloads", "router"),
    "media_router": ("backend.routers.media", "router"),
    "render_router": ("backend.routers.render", "router"),
    "system_router": ("backend.routers.system", "router"),
}

__all__ = list(_ROUTER_EXPORTS)


def __getattr__(name: str) -> Any:
    target = _ROUTER_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value
