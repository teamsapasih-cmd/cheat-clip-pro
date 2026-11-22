# Cloud upload staging verification

The unit suite verifies that the S3 SigV4 presigned PUT includes the exact
`Content-Length` and `Content-Type` request headers in its signed-header list.
This opt-in integration test checks that the configured S3-compatible provider
actually enforces the signed byte length.

## Safety guard

Run only against an isolated, non-production bucket. The test refuses to run
unless both environment flags are explicitly set:

- `CLOUD_STORAGE_ENVIRONMENT=staging`
- `CLOUD_STORAGE_INTEGRATION=1`

Do not set these flags in production.

## Required staging variables

Use the existing cloud storage environment variables, populated with staging
credentials and a staging bucket only:

- `OBJECT_STORAGE_ENDPOINT`
- `OBJECT_STORAGE_BUCKET`
- `OBJECT_STORAGE_ACCESS_KEY`
- `OBJECT_STORAGE_SECRET_KEY`
- `OBJECT_STORAGE_REGION`

## Run

```bash
CLOUD_STORAGE_ENVIRONMENT=staging CLOUD_STORAGE_INTEGRATION=1 \
  python -m pytest -q tests/integration/test_s3_upload_contract.py
```

The test performs one exact-size upload, verifies its metadata, then attempts a
larger body using a URL signed for the smaller size. It deletes both test object
keys in a `finally` block. A provider that accepts the oversized request fails
the test.

The normal CI job runs this test without the opt-in flags, so it is safely
skipped unless a staging environment explicitly supplies them.
