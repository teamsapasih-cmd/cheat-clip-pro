"""Cloud readiness and liveness probes for container hosting."""
from __future__ import annotations
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from backend.cloud.factory import build_job_queue, build_object_storage
from backend.database.session import build_engine

router = APIRouter(tags=["Cloud Health"])
logger = logging.getLogger(__name__)

@router.get("/api/health/live")
def liveness():
    return {"status": "ok", "service": "clip-intelligence-api"}

@router.get("/api/health/ready")
def readiness():
    checks: dict[str, str] = {}
    try:
        engine = build_engine()
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            checks["database"] = "ok"
        finally:
            engine.dispose()
    except Exception:
        checks["database"] = "unavailable"
    try:
        queue = build_job_queue()
        queue.client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"
    try:
        storage = build_object_storage()
        storage.check_bucket()
        checks["object_storage"] = "ok"
    except Exception as exc:
        # Log only sanitized diagnostic metadata; never log credentials or signed URLs.
        response = getattr(exc, "response", {})
        error = response.get("Error", {}) if isinstance(response, dict) else {}
        metadata = response.get("ResponseMetadata", {}) if isinstance(response, dict) else {}
        logger.warning(
            "Object storage readiness failed: exception=%s error_code=%s http_status=%s",
            type(exc).__name__,
            error.get("Code", "n/a"),
            metadata.get("HTTPStatusCode", "n/a"),
        )
        checks["object_storage"] = "unavailable"
    ready = all(value == "ok" for value in checks.values())
    body = {"status": "ready" if ready else "not_ready", "checks": checks}
    return body if ready else JSONResponse(status_code=503, content=body)
