from urllib.parse import parse_qs, urlparse

import pytest

from backend.cloud.s3_storage import S3ObjectStorage


def test_presigned_put_binds_exact_content_length():
    storage = S3ObjectStorage(
        endpoint_url="https://storage.example.test",
        bucket="private-media",
        access_key="test-access",
        secret_key="test-secret",
        region="us-east-1",
    )

    url = storage.create_upload_url(
        "users/user-1/project-1/asset-1/source.mp4",
        "video/mp4",
        expires_seconds=300,
        expected_size_bytes=123456,
    )

    query = parse_qs(urlparse(url).query)
    signed_headers = query["X-Amz-SignedHeaders"][0].split(";")
    assert "content-length" in signed_headers
    assert "content-type" in signed_headers
    assert query["X-Amz-Expires"] == ["300"]


def test_presigned_put_rejects_non_positive_expected_size():
    storage = S3ObjectStorage(
        endpoint_url="https://storage.example.test",
        bucket="private-media",
        access_key="test-access",
        secret_key="test-secret",
        region="us-east-1",
    )

    with pytest.raises(ValueError, match="positive number of bytes"):
        storage.create_upload_url(
            "users/user-1/source.mp4",
            "video/mp4",
            expected_size_bytes=0,
        )
