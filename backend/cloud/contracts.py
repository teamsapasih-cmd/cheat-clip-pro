"""Provider-neutral contracts for durable media storage and background jobs.

Concrete adapters (S3-compatible storage, Redis queue, etc.) will implement these
contracts in the cloud-infrastructure phase. No network clients are created here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class StoredObject:
    key: str
    size_bytes: int
    content_type: str


@dataclass(frozen=True)
class JobReceipt:
    job_id: str
    job_type: str
    status: str
    created_at: datetime


class ObjectStorage(Protocol):
    def put(
        self,
        key: str,
        body: BinaryIO,
        content_type: str,
    ) -> StoredObject:
        """Store an object in a private bucket and return its metadata."""
        ...

    def open(self, key: str) -> BinaryIO:
        """Open a stored object for controlled server-side reading."""
        ...

    def delete(self, key: str) -> None:
        """Delete an object after authorization and retention checks."""
        ...

    def create_upload_url(
        self, key: str, content_type: str, expires_seconds: int = 300,
        expected_size_bytes: int | None = None,
    ) -> str:
        """Create a short-lived upload URL bound to the declared object size."""
        ...


class JobQueue(Protocol):
    def enqueue(self, job_type: str, payload: dict[str, object]) -> JobReceipt:
        """Enqueue a durable, idempotent background job."""
        ...

    def cancel(self, job_id: str) -> bool:
        """Request cancellation; workers must still check cancellation cooperatively."""
        ...
