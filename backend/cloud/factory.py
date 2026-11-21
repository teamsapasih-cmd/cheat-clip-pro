"""Explicit factory functions for cloud adapters."""
from __future__ import annotations

from backend.cloud.redis_queue import RedisStreamJobQueue
from backend.cloud.s3_storage import S3ObjectStorage


def build_job_queue() -> RedisStreamJobQueue:
    return RedisStreamJobQueue.from_env()


def build_object_storage() -> S3ObjectStorage:
    return S3ObjectStorage.from_env()
