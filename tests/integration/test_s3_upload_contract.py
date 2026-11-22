"""Opt-in integration test for the S3-compatible signed upload contract.

This test is deliberately disabled unless CLOUD_STORAGE_ENVIRONMENT=staging and
CLOUD_STORAGE_INTEGRATION=1 are both set. Never point it at production storage.
"""
from __future__ import annotations

import os
import uuid

import pytest
import requests
from botocore.exceptions import ClientError

from backend.cloud.s3_storage import S3ObjectStorage


pytestmark = pytest.mark.skipif(
    os.environ.get("CLOUD_STORAGE_ENVIRONMENT", "").lower() != "staging"
    or os.environ.get("CLOUD_STORAGE_INTEGRATION") != "1",
    reason="Requires explicit opt-in to a non-production cloud storage environment",
)


def _assert_object_missing(storage: S3ObjectStorage, key: str) -> None:
    try:
        storage.get_metadata(key)
    except ClientError as error:
        code = str(error.response.get("Error", {}).get("Code", ""))
        status_code = int(error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))
        assert status_code == 404 or code in {"404", "NoSuchKey", "NotFound"}, (
            f"Expected rejected upload object to be absent; storage returned {code or status_code}"
        )
        return
    pytest.fail("Storage contains an object from a rejected oversized upload")


def test_staging_storage_enforces_signed_content_length_and_cleanup():
    storage = S3ObjectStorage.from_env()
    prefix = f"ci-staging-upload-contract/{uuid.uuid4().hex}"
    content_type = "application/octet-stream"
    payload = b"clip-studio-staging-upload-contract"

    exact_key = f"{prefix}/exact-size.bin"
    oversized_key = f"{prefix}/oversized.bin"

    try:
        exact_url = storage.create_upload_url(
            exact_key,
            content_type,
            expires_seconds=120,
            expected_size_bytes=len(payload),
        )
        exact_response = requests.put(
            exact_url,
            data=payload,
            headers={"Content-Type": content_type},
            timeout=30,
        )
        assert exact_response.status_code in (200, 201, 204), (
            f"Staging provider rejected an exact-size signed PUT: "
            f"HTTP {exact_response.status_code}"
        )
        exact_metadata = storage.get_metadata(exact_key)
        assert exact_metadata["size_bytes"] == len(payload)
        assert exact_metadata["content_type"] == content_type

        oversized_url = storage.create_upload_url(
            oversized_key,
            content_type,
            expires_seconds=120,
            expected_size_bytes=len(payload),
        )
        oversized_response = requests.put(
            oversized_url,
            data=payload + b"x",
            headers={"Content-Type": content_type},
            timeout=30,
        )
        assert oversized_response.status_code in (400, 403, 411, 413), (
            "Expected the provider to reject a body whose Content-Length differs "
            f"from the signed size; received HTTP {oversized_response.status_code}"
        )
        _assert_object_missing(storage, oversized_key)
    finally:
        cleanup_errors = []
        for key in (exact_key, oversized_key):
            try:
                storage.delete(key)
            except Exception as error:
                cleanup_errors.append(f"{key}: {type(error).__name__}")
        if cleanup_errors:
            pytest.fail("Staging integration cleanup failed: " + "; ".join(cleanup_errors))
