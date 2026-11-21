"""Private S3-compatible object storage adapter."""
from __future__ import annotations

import os
from typing import BinaryIO

import boto3
from botocore.config import Config

from backend.cloud.contracts import StoredObject


class S3ObjectStorage:
    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("A private object storage bucket is required")
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region or "auto",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 4},
                # Supabase Storage S3 expects path-style bucket addressing.
                # This style is also supported by Cloudflare R2.
                s3={"addressing_style": "path"},
            ),
        )

    @classmethod
    def from_env(cls) -> "S3ObjectStorage":
        required = [
            "OBJECT_STORAGE_BUCKET",
            "OBJECT_STORAGE_ACCESS_KEY",
            "OBJECT_STORAGE_SECRET_KEY",
        ]
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise RuntimeError("Missing object storage settings: " + ", ".join(missing))
        return cls(
            endpoint_url=os.environ.get("OBJECT_STORAGE_ENDPOINT", ""),
            bucket=os.environ["OBJECT_STORAGE_BUCKET"],
            access_key=os.environ["OBJECT_STORAGE_ACCESS_KEY"],
            secret_key=os.environ["OBJECT_STORAGE_SECRET_KEY"],
            region=os.environ.get("OBJECT_STORAGE_REGION"),
        )

    def put(self, key: str, body: BinaryIO, content_type: str) -> StoredObject:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("Storage key must be a safe relative object key")
        self.client.upload_fileobj(
            body,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type or "application/octet-stream"},
        )
        head = self.client.head_object(Bucket=self.bucket, Key=key)
        return StoredObject(
            key=key,
            size_bytes=int(head["ContentLength"]),
            content_type=head.get("ContentType", content_type),
        )

    def create_upload_url(self, key: str, content_type: str, expires_seconds: int = 300) -> str:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("Storage key must be a safe relative object key")
        if not 1 <= expires_seconds <= 900:
            raise ValueError("Signed upload URL expiry must be between 1 and 900 seconds")
        return self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type or "application/octet-stream",
            },
            ExpiresIn=expires_seconds,
        )

    def get_metadata(self, key: str) -> dict[str, object]:
        head = self.client.head_object(Bucket=self.bucket, Key=key)
        return {
            "size_bytes": int(head["ContentLength"]),
            "content_type": str(head.get("ContentType", "application/octet-stream")),
        }

    def open(self, key: str) -> BinaryIO:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"]

    def check_bucket(self) -> None:
        """Raise if the configured private bucket cannot be reached."""
        self.client.head_bucket(Bucket=self.bucket)

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def create_download_url(self, key: str, expires_seconds: int = 300) -> str:
        if not 1 <= expires_seconds <= 3600:
            raise ValueError("Signed URL expiry must be between 1 and 3600 seconds")
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
