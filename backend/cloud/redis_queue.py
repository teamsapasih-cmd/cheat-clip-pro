"""Redis-backed job queue adapter using Redis Streams.

Jobs are stored durably in a Redis stream and can be consumed by independently
deployed workers. A consumer group distributes work and supports acknowledgments.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from redis import Redis
from redis.exceptions import ResponseError

from backend.cloud.contracts import JobReceipt


class RedisStreamJobQueue:
    def __init__(
        self,
        client: Redis,
        stream_key: str = "clipstudio:jobs",
        group_name: str = "clipstudio-workers",
    ) -> None:
        self.client = client
        self.stream_key = stream_key
        self.group_name = group_name
        try:
            self.client.xgroup_create(self.stream_key, self.group_name, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    @classmethod
    def from_env(cls) -> "RedisStreamJobQueue":
        url = os.environ.get("REDIS_URL")
        if not url:
            raise RuntimeError("REDIS_URL is required to initialize the job queue")
        return cls(Redis.from_url(url, decode_responses=True))

    def enqueue(self, job_type: str, payload: dict[str, object]) -> JobReceipt:
        if not job_type or len(job_type) > 100:
            raise ValueError("job_type must contain 1 to 100 characters")
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.client.xadd(
            self.stream_key,
            {
                "job_id": job_id,
                "job_type": job_type,
                "payload": json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                "created_at": now.isoformat(),
                "status": "queued",
            },
        )
        return JobReceipt(job_id=job_id, job_type=job_type, status="queued", created_at=now)

    def read(self, consumer: str, count: int = 1, block_ms: int = 5000) -> list[dict[str, Any]]:
        if count < 1 or count > 100:
            raise ValueError("count must be between 1 and 100")
        batches = self.client.xreadgroup(
            self.group_name, consumer, {self.stream_key: ">"}, count=count, block=block_ms
        )
        jobs: list[dict[str, Any]] = []
        for _, entries in batches:
            for entry_id, fields in entries:
                fields["stream_entry_id"] = entry_id
                fields["payload"] = json.loads(fields.get("payload", "{}"))
                jobs.append(fields)
        return jobs

    def acknowledge(self, stream_entry_id: str) -> None:
        self.client.xack(self.stream_key, self.group_name, stream_entry_id)

    def cancel(self, job_id: str) -> bool:
        # Cancellation is cooperative: workers inspect this marker between stages.
        return bool(self.client.set(f"clipstudio:cancel:{job_id}", "1", ex=86400))

    def is_cancelled(self, job_id: str) -> bool:
        return bool(self.client.exists(f"clipstudio:cancel:{job_id}"))
