"""Redis Streams queue with retry, stale-job recovery and progress metadata."""
from __future__ import annotations
import json, os, uuid
from datetime import datetime, timezone
from typing import Any
from redis import Redis
from redis.exceptions import ResponseError
from backend.cloud.contracts import JobReceipt

class RedisStreamJobQueue:
    def __init__(self, client: Redis, stream_key: str = "clipstudio:jobs",
                 group_name: str = "clipstudio-workers", dead_letter_key: str | None = None):
        self.client, self.stream_key, self.group_name = client, stream_key, group_name
        self.dead_letter_key = dead_letter_key or f"{stream_key}:dead"
        try:
            self.client.xgroup_create(self.stream_key, self.group_name, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc): raise

    @classmethod
    def from_env(cls):
        url = os.environ.get("REDIS_URL")
        if not url: raise RuntimeError("REDIS_URL is required to initialize the job queue")
        return cls(Redis.from_url(url, decode_responses=True, socket_timeout=15, socket_connect_timeout=10))

    @staticmethod
    def _decode_entry(entry_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        decoded = dict(fields)
        decoded["stream_entry_id"] = entry_id
        decoded["payload"] = json.loads(decoded.get("payload", "{}"))
        decoded["attempt"] = int(decoded.get("attempt", 0))
        return decoded

    def enqueue(self, job_type: str, payload: dict[str, object]) -> JobReceipt:
        if not job_type or len(job_type) > 100: raise ValueError("job_type must contain 1 to 100 characters")
        job_id, now = str(uuid.uuid4()), datetime.now(timezone.utc)
        self.client.xadd(self.stream_key, {
            "job_id": job_id, "job_type": job_type,
            "payload": json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            "created_at": now.isoformat(), "status": "queued", "attempt": "0",
        })
        self.update_progress(job_id, "queued", 0)
        return JobReceipt(job_id=job_id, job_type=job_type, status="queued", created_at=now)

    def read(self, consumer: str, count: int = 1, block_ms: int = 5000) -> list[dict[str, Any]]:
        if count < 1 or count > 100: raise ValueError("count must be between 1 and 100")
        batches = self.client.xreadgroup(self.group_name, consumer, {self.stream_key: ">"}, count=count, block=block_ms)
        return [self._decode_entry(eid, fields) for _, entries in batches for eid, fields in entries]

    def claim_stale(self, consumer: str, min_idle_ms: int = 60_000, count: int = 10) -> list[dict[str, Any]]:
        result = self.client.xautoclaim(self.stream_key, self.group_name, consumer, min_idle_ms, "0-0", count=count)
        entries = result[1] if result and len(result) > 1 else []
        return [self._decode_entry(eid, fields) for eid, fields in entries]

    def acknowledge(self, stream_entry_id: str) -> None:
        self.client.xack(self.stream_key, self.group_name, stream_entry_id)

    def update_progress(self, job_id: str, status: str, progress: int, detail: str | None = None) -> None:
        if not 0 <= int(progress) <= 100: raise ValueError("progress must be between 0 and 100")
        values = {"job_id": job_id, "status": status, "progress": str(int(progress)),
                  "updated_at": datetime.now(timezone.utc).isoformat()}
        if detail: values["detail"] = detail[:500]
        key = f"clipstudio:job:{job_id}"
        self.client.hset(key, mapping=values)
        self.client.expire(key, 7 * 24 * 60 * 60)

    def get_progress(self, job_id: str) -> dict[str, str] | None:
        result = self.client.hgetall(f"clipstudio:job:{job_id}")
        return result or None

    def cancel(self, job_id: str) -> bool:
        return bool(self.client.set(f"clipstudio:cancel:{job_id}", "1", ex=86400))

    def is_cancelled(self, job_id: str) -> bool:
        return bool(self.client.exists(f"clipstudio:cancel:{job_id}"))

    def dead_letter(self, job: dict[str, Any], reason: str) -> None:
        self.client.xadd(self.dead_letter_key, {
            "job_id": str(job["job_id"]), "job_type": str(job.get("job_type", "unknown")),
            "payload": json.dumps(job.get("payload", {}), ensure_ascii=False),
            "reason": reason[:1000], "failed_at": datetime.now(timezone.utc).isoformat(),
            "attempt": str(job.get("attempt", 0)),
        })
        self.acknowledge(str(job["stream_entry_id"]))
        self.update_progress(str(job["job_id"]), "failed", 100, reason)

    def retry_or_dead_letter(self, job: dict[str, Any], error: str, max_attempts: int = 3) -> bool:
        attempt = int(job.get("attempt", 0)) + 1
        if attempt >= max_attempts:
            self.dead_letter(job, error)
            return False
        self.client.xadd(self.stream_key, {
            "job_id": str(job["job_id"]), "job_type": str(job["job_type"]),
            "payload": json.dumps(job.get("payload", {}), ensure_ascii=False),
            "created_at": str(job.get("created_at", datetime.now(timezone.utc).isoformat())),
            "status": "retrying", "attempt": str(attempt), "last_error": error[:1000],
        })
        self.acknowledge(str(job["stream_entry_id"]))
        self.update_progress(str(job["job_id"]), "retrying", 0, error)
        return True
