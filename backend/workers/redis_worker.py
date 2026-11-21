"""Reliable Redis Streams worker with retry and crash recovery."""
from __future__ import annotations
import logging, os, socket, time
from typing import Callable
from backend.cloud.redis_queue import RedisStreamJobQueue

logger = logging.getLogger("clipstudio.worker")
Handler = Callable[[dict[str, object]], None]

def run_worker(handlers: dict[str, Handler] | None = None) -> None:
    queue = RedisStreamJobQueue.from_env()
    consumer = os.environ.get("WORKER_NAME") or socket.gethostname()
    registered = handlers or {}
    max_attempts = max(1, int(os.environ.get("WORKER_MAX_ATTEMPTS", "3")))
    reclaim_idle_ms = max(10_000, int(os.environ.get("WORKER_RECLAIM_IDLE_MS", "60000")))
    logger.info("Worker %s started; registered handlers: %s", consumer, sorted(registered))
    while True:
        jobs = queue.claim_stale(consumer, min_idle_ms=reclaim_idle_ms, count=5)
        if not jobs:
            jobs = queue.read(consumer=consumer, count=1, block_ms=5000)
        for job in jobs:
            entry_id, job_id, job_type = str(job["stream_entry_id"]), str(job["job_id"]), str(job["job_type"])
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
                queue.update_progress(job_id, "processing", 1)
                handler(job["payload"])
                queue.update_progress(job_id, "completed", 100)
                queue.acknowledge(entry_id)
            except Exception as exc:
                logger.exception("Job %s failed on attempt %s", job_id, int(job.get("attempt", 0)) + 1)
                try:
                    retry = queue.retry_or_dead_letter(job, f"{type(exc).__name__}: {exc}", max_attempts)
                    if retry: time.sleep(min(2 ** (int(job.get("attempt", 0)) + 1), 30))
                except Exception:
                    logger.exception("Could not persist retry state for job %s; leaving it pending", job_id)

if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    run_worker()
