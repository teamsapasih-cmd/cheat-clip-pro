"""Small, dependency-light Redis Streams worker lease helper."""
from __future__ import annotations

import logging
from threading import Event, Thread
from typing import Any

logger = logging.getLogger("clipstudio.worker")


def start_job_heartbeat(
    queue: Any,
    consumer: str,
    entry_id: str,
    interval_seconds: float,
) -> tuple[Event, Thread]:
    """Keep a long-running Redis Streams entry owned by this worker."""
    if interval_seconds <= 0:
        raise ValueError("Heartbeat interval must be greater than zero")

    stop_event = Event()

    def heartbeat_loop() -> None:
        while not stop_event.wait(interval_seconds):
            try:
                if not queue.heartbeat(consumer, entry_id):
                    logger.warning("Worker lease refresh returned no pending entry: %s", entry_id)
            except Exception:
                # A transient heartbeat error is observable but must not kill the
                # actual job handler. Redis reclaim remains the crash-recovery path.
                logger.exception("Could not refresh worker lease for entry %s", entry_id)

    thread = Thread(
        target=heartbeat_loop,
        name=f"clipstudio-lease-{entry_id}",
        daemon=True,
    )
    thread.start()
    return stop_event, thread
