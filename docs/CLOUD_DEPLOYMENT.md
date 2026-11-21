# Clip Intelligence Studio — cloud deployment

Deploy two Railway services from this repository and branch `clip-intelligence-upgrade`.
Both use the root Dockerfile image.

## API / web service
- Build: root `Dockerfile`
- Start: Dockerfile default (Uvicorn on `0.0.0.0:$PORT`)
- Health check path: `/api/health/live`
- Expose a public domain on this service only.

## Analysis worker service
- Build: same repository, branch and root Dockerfile
- Start command override: `python -m backend.workers.redis_worker`
- No public domain required; start with one replica.

## Required secret Variables (API and worker)

- `DATABASE_URL`: Supabase PostgreSQL connection string. Prefer the Supabase Session Pooler (port 5432) for persistent application/worker connections; require SSL.
- `REDIS_URL`: private Redis connection URL from the Railway Redis service.
- `OBJECT_STORAGE_ENDPOINT`: Supabase S3 endpoint for 50 MB smoke tests, or Cloudflare R2 endpoint for large videos.
- `OBJECT_STORAGE_REGION`: `ap-south-1` for Supabase or `auto` for R2.
- `OBJECT_STORAGE_BUCKET`: `clipstudio-private-media`
- `OBJECT_STORAGE_ACCESS_KEY` and `OBJECT_STORAGE_SECRET_KEY`: generated under Supabase Dashboard → Storage → S3 Configuration → Access keys.
- `JWT_SECRET_KEY`: long random secret (at least 32 random bytes).
- `GEMINI_API_KEY`: provider key for the worker, unless the request uses OpenRouter.
- `CLOUD_REQUIRE_INFRASTRUCTURE`: `1`
- `MAX_CLOUD_UPLOAD_BYTES`: `2147483648`
- `ALLOWED_ORIGINS`: deployed web origin. If the frontend is served by this API, use that same origin.

Never commit real values or send credentials in chat. Configure secrets only in the hosting provider Variables UI.

## Storage provider choice

A private bucket `clipstudio-private-media` exists in Supabase Storage. Its bucket-level cap is 2 GiB, but the connected Supabase organization is currently on the Free plan: Supabase enforces a **50 MB global upload limit** on Free projects. The effective limit is the lower of the global and bucket limits.

For initial smoke tests, keep `MAX_CLOUD_UPLOAD_BYTES=52428800` (50 MB) and use the Supabase S3 endpoint. For the intended large-video workflow, use an S3-compatible provider such as Cloudflare R2 and set `MAX_CLOUD_UPLOAD_BYTES=2147483648` (2 GiB) after creating the bucket and credentials. R2 uses endpoint `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`, region `auto`, and a private bucket named `clipstudio-private-media`.

S3 access keys are separate from Supabase publishable/anon keys. Never put them in Git or chat.

## Database
Run the migration release command before serving traffic:
`alembic -c alembic.ini upgrade head`

The application uses the `clipstudio_*` table namespace to avoid collisions with other applications in this Supabase project.

## Verification
- API liveness: `/api/health/live`
- Infrastructure readiness: `/api/health/ready`
- Worker logs must show `analysis.run` registered.
- Upload an authorized test video, verify upload completion, enqueue analysis, and confirm analysis + clip candidates persist.

Do not mark production-ready until end-to-end upload, worker execution, retries, tenant isolation and result persistence pass.


## Automatic data retention (default policy)

Large binary objects are temporary by default:
- Original uploaded source media: deleted 7 days after upload verification; successful analysis refreshes the expiry to 7 days after analysis completion.
- Rendered exports: deleted when their `expires_at` timestamp is reached. Render/export creation must set this timestamp (default 7 days).
- Worker temporary files: deleted immediately after each analysis attempt, including failed attempts.
- Analysis metadata, transcript text, clip suggestions and project/editing metadata remain in PostgreSQL; they are comparatively small and preserve useful work. A separate account-level retention policy can later expire these records (default 90 days) with user-visible notice and export options.
- Assets with queued or processing analysis jobs are never deleted by the retention sweep.
- Storage deletion is idempotent at the application level: successful deletion clears the object key / records `storage_deleted_at`; failures are logged and retried in the next sweep.

Environment variables:
- `SOURCE_MEDIA_RETENTION_DAYS=7`
- `RETENTION_SWEEP_INTERVAL_SECONDS=900`
- Render/export services should set `expires_at` to `now + EXPORT_RETENTION_DAYS` (default 7 days).

Retention cleanup runs in the dedicated worker; no extra scheduler or local installation is required.
