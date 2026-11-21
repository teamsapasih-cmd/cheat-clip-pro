"""Reliable Redis Streams worker with database-backed analysis lifecycle."""
from __future__ import annotations

import logging
import os
import socket
import time
from functools import lru_cache
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.cloud.redis_queue import RedisStreamJobQueue
from backend.database.models import Analysis
from backend.database.session import build_engine, build_session_factory
from backend.services.analysis_persistence import persist_analysis_result

logger = logging.getLogger("clipstudio.worker")
Handler = Callable[[dict[str, object]], None]


@lru_cache(maxsize=1)
def _session_factory():
    """Create one reusable worker DB pool, lazily and only inside the worker."""
    return build_session_factory(build_engine())


def _set_analysis_state(
    payload: dict[str, object],
    status: str,
    error_message: str | None = None,
) -> None:
    """Update an analysis only when both its id and tenant owner are present."""
    analysis_id = payload.get("analysis_id")
    owner_id = payload.get("owner_id")
    if not analysis_id or not owner_id:
        return

    db: Session = _session_factory()()
    try:
        analysis = db.scalar(
            select(Analysis).where(
                Analysis.id == str(analysis_id),
                Analysis.owner_id == str(owner_id),
            )
        )
        if analysis is None:
            logger.warning("Analysis lifecycle update skipped: record not found")
            return
        analysis.status = status
        if error_message is not None:
            analysis.error_message = error_message[:2000]
        elif status in {"queued", "processing", "completed"}:
            analysis.error_message = None
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _persist_analysis_result(payload: dict[str, object]) -> None:
    required = ("analysis_id", "owner_id", "result")
    if any(key not in payload for key in required):
        raise ValueError("analysis.persist_result payload is incomplete")
    if not isinstance(payload["result"], dict):
        raise ValueError("analysis.persist_result result must be an object")

    db: Session = _session_factory()()
    try:
        persist_analysis_result(
            db,
            analysis_id=str(payload["analysis_id"]),
            owner_id=str(payload["owner_id"]),
            result=payload["result"],
        )
    finally:
        db.close()


def run_worker(handlers: dict[str, Handler] | None = None) -> None:
    queue = RedisStreamJobQueue.from_env()
    consumer = os.environ.get("WORKER_NAME") or socket.gethostname()
    registered = {"analysis.persist_result": _persist_analysis_result}
    if handlers:
        registered.update(handlers)

    max_attempts = max(1, int(os.environ.get("WORKER_MAX_ATTEMPTS", "3")))
    reclaim_idle_ms = max(10_000, int(os.environ.get("WORKER_RECLAIM_IDLE_MS", "60000")))
    logger.info("Worker %s started; registered handlers: %s", consumer, sorted(registered))

    while True:
        jobs = queue.claim_stale(consumer, min_idle_ms=reclaim_idle_ms, count=5)
        if not jobs:
            jobs = queue.read(consumer=consumer, count=1, block_ms=5000)

        for job in jobs:
            entry_id = str(job["stream_entry_id"])
            job_id = str(job["job_id"])
            job_type = str(job["job_type"])
            payload = job.get("payload") or {}

            try:
                handler = registered.get(job_type)
                if handler is None:
                    reason = f"Unsupported job type: {job_type}"
                    queue.dead_letter(job, reason)
                    _set_analysis_state(payload, "failed", reason)
                    logger.error("Moved unsupported job %s to dead-letter stream", job_id)
                    continue

                if queue.is_cancelled(job_id):
                    _set_analysis_state(payload, "cancelled", "Job was cancelled")
                    queue.update_progress(job_id, "cancelled", 100)
                    queue.acknowledge(entry_id)
                    continue

                _set_analysis_state(payload, "processing")
                queue.update_progress(job_id, "processing", 5)
                handler(payload)
                queue.update_progress(job_id, "completed", 100)
                queue.acknowledge(entry_id)

            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                logger.exception(
                    "Job %s failed on attempt %s",
                    job_id,
                    int(job.get("attempt", 0)) + 1,
                )
                try:
                    retry = queue.retry_or_dead_letter(job, error, max_attempts)
                    if retry:
                        _set_analysis_state(payload, "queued", error)
                        time.sleep(min(2 ** (int(job.get("attempt", 0)) + 1), 30))
                    else:
                        _set_analysis_state(payload, "failed", error)
                except Exception:
                    logger.exception(
                        "Could not persist retry state for job %s; leaving it pending",
                        job_id,
                    )


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    run_worker()
