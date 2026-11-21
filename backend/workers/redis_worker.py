"""Minimal Redis Streams worker process entrypoint.

This worker deliberately dispatches only registered job handlers. Unknown job
types are never evaluated dynamically and are acknowledged after being recorded
as unsupported to prevent an infinite poison-message loop.
"""
from __future__ import annotations

import logging
import os
import socket
import time
from typing import Callable

from backend.cloud.redis_queue import RedisStreamJobQueue

logger = logging.getLogger("clipstudio.worker")
Handler = Callable[[dict[str, object]], None]


def run_worker(handlers: dict[str, Handler] | None = None) -> None:
    queue = RedisStreamJobQueue.from_env()
    consumer = os.environ.get("WORKER_NAME") or socket.gethostname()
    registered = handlers or {}

    logger.info("Worker %s started; registered handlers: %s", consumer, sorted(registered))
    while True:
        jobs = queue.read(consumer=consumer, count=1, block_ms=5000)
        for job in jobs:
            entry_id = str(job["stream_entry_id"])
            job_id = str(job["job_id"])
            job_type = str(job["job_type"])
            try:
                handler = registered.get(job_type)
                if handler is None:
                    logger.error("No handler registered for job type %s (job %s)", job_type, job_id)
                elif queue.is_cancelled(job_id):
                    logger.info("Job %s was cancelled before processing", job_id)
                else:
                    handler(job["payload"])
            except Exception:
                logger.exception("Job %s failed", job_id)
            finally:
                queue.acknowledge(entry_id)


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    run_worker()
