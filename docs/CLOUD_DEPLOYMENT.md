# Clip Intelligence Studio — cloud deployment

Deploy the API/web service and a separate analysis worker from this repository and branch `clip-intelligence-upgrade`.

## API / web service
- Build: root `Dockerfile`
- Start: Dockerfile default (Uvicorn on `0.0.0.0:$PORT`)
- Health check path: `/api/health/live`
- Expose a public domain on this service only.

## Analysis worker
- Build: same repository, branch and root Dockerfile
- Start command override: `python -m backend.workers.redis_worker`
- No public domain required.

## Current storage provider: Supabase Storage

The existing private bucket is `clipstudio-private-media`. S3 protocol is enabled in the Supabase dashboard and an access key named `clipping` is visible there.

Use these values in Railway Variables for both API and worker:
- `OBJECT_STORAGE_ENDPOINT=https://luelliccbrgwlrkdfhrw.storage.supabase.co/storage/v1/s3`
- `OBJECT_STORAGE_REGION=ap-south-1`
- `OBJECT_STORAGE_BUCKET=clipstudio-private-media`
- `OBJECT_STORAGE_ACCESS_KEY`: the Access Key ID for the Supabase key named `clipping`
- `OBJECT_STORAGE_SECRET_KEY`: the matching Secret Access Key, available only when initially created (or after rotating/creating a replacement).

The Access Key ID shown in the dashboard is not the Secret Access Key. Do not paste either secret into chat, source files, frontend variables or Git. If the secret was not saved when the key was created, create a new S3 access key in Supabase and copy its secret directly into Railway Variables; then remove the old key after verifying the replacement works.

Supabase Free currently has a 50 MB global per-file upload limit, even though the bucket itself is configured for a 2 GiB cap. Enforce `MAX_CLOUD_UPLOAD_BYTES=50000000` while using this plan. Larger files must be rejected before upload. Do not raise this limit unless the provider plan/limit has actually changed.

## Required remaining service variables
- `DATABASE_URL`: Supabase PostgreSQL connection string; prefer Session Pooler and require SSL.
- `REDIS_URL`: private Redis connection URL from Railway Redis.
- `JWT_SECRET_KEY`: random secret of at least 32 characters.
- `GEMINI_API_KEY` or `OPENROUTER_API_KEY`: server-side AI provider key.
- `CLOUD_REQUIRE_INFRASTRUCTURE=0` until all required services are configured and verified; set to `1` only before production readiness checks.
- `ALLOWED_ORIGINS`: deployed web origin.

Configure all secrets only in Railway Variables. Never commit real values or send credentials in chat.

## Optional future Cloudflare R2

Cloudflare R2 is not required for the current no-card setup. If activated later, replace the Supabase S3 endpoint, region and credentials with R2 values. The provider-neutral S3 adapter can then be reused.

## Database
Run `alembic -c alembic.ini upgrade head` before serving traffic.

## Verification before production
- API liveness: `/api/health/live`
- API readiness: `/api/health/ready`
- Worker logs show `analysis.run` registered.
- Upload an authorized test video under the active provider limit, verify upload completion, enqueue analysis and confirm results persist.
- Verify tenant isolation, retries, cancellation and retention behavior.

Do not mark production-ready until end-to-end tests pass.

## Automatic data retention

- Original uploaded source media: deleted 7 days after upload verification; successful analysis refreshes expiry to 7 days after analysis completion.
- Cloud exports: deleted when `expires_at` is reached; the database record is retained.
- Worker temporary files: removed after each analysis attempt.
- Analysis metadata, transcript text and clip suggestions remain in PostgreSQL.
- Assets with queued or processing analysis jobs are protected from source-media cleanup.
- Legacy local render files remain on disk until a separate safe local-disk cleanup policy is implemented.

Defaults: `SOURCE_MEDIA_RETENTION_DAYS=7`, `EXPORT_RETENTION_DAYS=7`, `RETENTION_SWEEP_INTERVAL_SECONDS=900`.
