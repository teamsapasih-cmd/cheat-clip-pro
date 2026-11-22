"""Opt-in integration test for the S3-compatible signed upload contract.

This test is deliberately disabled unless CLOUD_STORAGE_ENVIRONMENT=staging and
CLOUD_STORAGE_INTEGRATION=1 are both set. Never point it at production storage.
"""
from __future__ import annotations

import os
import uuid

import pytest
import requests

from backend.cloud.s3_storage import S3ObjectStorage


pytestmark = pytest.mark.skipif(
    os.environ.get("CLOUD_STORAGE_ENVIRONMENT", "").lower() != "staging"
    or os.environ.get("CLOUD_STORAGE_INTEGRATION") != "1",
    reason="Requires explicit opt-in to a non-production cloud storage environment",
)


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
        assert storage.get_metadata(exact_key)["size_bytes"] == len(payload)

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
        assert not 200 <= oversized_response.status_code < 300, (
            "Staging provider accepted a PUT whose Content-Length differs "
            "from the signed size"
        )
    finally:
        storage.delete(exact_key)
        storage.delete(oversized_key)
