# Cloud upload staging verification

The unit suite verifies that the S3 SigV4 presigned PUT includes the exact
`Content-Length` and `Content-Type` request headers in its signed-header list.
This opt-in integration test checks that the configured S3-compatible provider
actually enforces the signed byte length.

## Safety guard

Run only against an isolated, non-production bucket and non-production
credentials. The test refuses to run unless both environment flags are
explicitly set:

- `CLOUD_STORAGE_ENVIRONMENT=staging`
- `CLOUD_STORAGE_INTEGRATION=1`

Do not set these flags in production. Do not copy production access keys into a
staging shell, CI secret, local environment, or test configuration.

## Staging resources required

Create or designate a dedicated staging bucket with:

- Private access; no public read or public write policy.
- A staging-only access key restricted to that bucket and required object
  operations (PUT, HEAD, and DELETE for this contract test; GET for later
  end-to-end analysis/export validation).
- A dedicated endpoint/region appropriate to the provider.
- A unique staging bucket name that cannot be confused with the production
  bucket.

For browser upload testing, configure bucket CORS for the exact non-production
frontend origin only. Permit the required `PUT` method and `Content-Type`
request header. Do not use a wildcard origin with credentials or expose the
bucket publicly. If the provider requires additional CORS response headers,
add only those required by the tested browser flow.

## Required staging variables

Populate these variables from a secure local secret store or the deployment's
staging-only secret manager. Never commit values to the repository or paste
credentials into pull request comments:

- `CLOUD_STORAGE_ENVIRONMENT=staging`
- `CLOUD_STORAGE_INTEGRATION=1`
- `OBJECT_STORAGE_ENDPOINT`
- `OBJECT_STORAGE_BUCKET`
- `OBJECT_STORAGE_ACCESS_KEY`
- `OBJECT_STORAGE_SECRET_KEY`
- `OBJECT_STORAGE_REGION`

## Run

```bash
python -m pytest -q tests/integration/test_s3_upload_contract.py
```

The test performs one exact-size upload, verifies its metadata, then attempts a
larger body using a URL signed for the smaller size. It verifies that the
rejected object's key is absent and attempts to delete both test keys in a
`finally` block. A provider that accepts the oversized request or leaves an
object behind fails the test. If cleanup itself fails, the test fails and the
staging bucket must be inspected before retrying.

## After the contract test

Before enabling the cloud workspace in any deployment, separately verify on
staging:

1. Browser CORS preflight and direct PUT from the exact staging frontend origin.
2. Upload completion verifies byte length and content type.
3. An abandoned pending intent expires and its object is deleted by retention.
4. A rejected upload object is removed; a transient delete failure is retried
   by a later retention sweep.
5. Upload -> queue -> worker -> analysis result -> render -> private export
   download works end to end.
6. Another account cannot read project, media, analysis, or export resources.
7. Expired source and export objects are removed according to the reviewed
   cloud retention policy.

Normal CI runs the integration test without opt-in flags, so it is safely
skipped unless a staging environment explicitly supplies the flags and
staging-only credentials. Passing the skip guard is not evidence that the
provider-level test or end-to-end staging flow has passed.