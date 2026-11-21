"""Reliable Redis Streams worker with database-backed result persistence."""
from __future__ import annotations
import logging, os, socket, time
from typing import Callable
from sqlalchemy.orm import Session
from backend.cloud.redis_queue import RedisStreamJobQueue
from backend.database.session import build_engine, build_session_factory
from backend.services.analysis_persistence import persist_analysis_result

logger = logging.getLogger("clipstudio.worker")
Handler = Callable[[dict[str, object]], None]

def _persist_analysis_result(payload: dict[str, object]) -> None:
    required = ("analysis_id", "owner_id", "result")
    if any(key not in payload for key in required):
        raise ValueError("analysis.persist_result payload is incomplete")
    if not isinstance(payload["result"], dict):
        raise ValueError("analysis.persist_result result must be an object")
    factory = build_session_factory(build_engine())
    db: Session = factory()
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
            entry_id, job_id = str(job["stream_entry_id"]), str(job["job_id"])
            job_type = str(job["job_type"])
            try:
                handler = registered.get(job_type)
                if handler is None:
                    queue.dead_letter(job, f"Unsupported job type: {job_type}")
                    logger.error("Moved unsupported job %s to dead-letter stream", job_id)
                    continue
                if queue.is_cancelled(job_id):
                    queue.update_progress(job_id, "cancelled", 100)
                    queue.acknowledge(entry_id)
                    continue
                queue.update_progress(job_id, "processing", 5)
                handler(job["payload"])
                queue.update_progress(job_id, "completed", 100)
                queue.acknowledge(entry_id)
            except Exception as exc:
                logger.exception("Job %s failed on attempt %s", job_id, int(job.get("attempt", 0)) + 1)
                try:
                    retry = queue.retry_or_dead_letter(job, f"{type(exc).__name__}: {exc}", max_attempts)
                    if retry:
                        time.sleep(min(2 ** (int(job.get("attempt", 0)) + 1), 30))
                except Exception:
                    logger.exception("Could not persist retry state for job %s; leaving it pending", job_id)

if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    run_worker()
