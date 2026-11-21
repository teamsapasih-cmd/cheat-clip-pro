# Clip Intelligence Studio — cloud deployment

Deploy two Railway services from this repository and branch `clip-intelligence-upgrade`.
Both use the root Dockerfile.

## API / web service
- Build: root `Dockerfile`
- Start: Dockerfile default (Uvicorn on `0.0.0.0:$PORT`)
- Health check path: `/api/health/live`
- Expose a public domain on this service only.

## Analysis worker service
- Build: same repository, branch and root Dockerfile
- Start command override: `python -m backend.workers.redis_worker`
- No public domain required; start with one replica.

## Required deployment variables

- `DATABASE_URL`: Supabase PostgreSQL connection string. Prefer the Supabase Session Pooler (port 5432) for persistent application/worker connections; require SSL.
- `REDIS_URL`: private Redis connection URL from the Railway Redis service.
- `OBJECT_STORAGE_ENDPOINT`: Supabase S3 endpoint from Storage > Configuration > S3.
- `OBJECT_STORAGE_REGION`: region shown in the Supabase S3 configuration (currently `ap-south-1` for this project).
- `OBJECT_STORAGE_BUCKET`: `clipstudio-private-media` (private Supabase Storage bucket).
- `OBJECT_STORAGE_ACCESS_KEY` and `OBJECT_STORAGE_SECRET_KEY`: generated Supabase Storage S3 credentials. These credentials provide broad access to Storage and bypass Storage RLS; use them only on the server, never in browser code.
- `JWT_SECRET_KEY`: long random secret (at least 32 random bytes).
- `GEMINI_API_KEY`: provider key for the worker, unless the request uses OpenRouter.
- `CLOUD_REQUIRE_INFRASTRUCTURE`: keep `0` until all infrastructure is configured and verified; change to `1` only for production readiness checks.
- `MAX_CLOUD_UPLOAD_BYTES`: `52428800` (50 MiB while using Supabase Free).
- `ALLOWED_ORIGINS`: deployed web origin. If the frontend is served by this API, use that same origin.

Never commit real values or send credentials in chat. Configure secrets only in the hosting provider Variables UI.

## Storage provider choice

The default storage adapter uses the existing private Supabase bucket `clipstudio-private-media` through Supabase's S3-compatible endpoint. Supabase Storage S3 credentials must be generated in the project's Storage configuration. They are server-side credentials with broad Storage access and must never be exposed to the browser.

The bucket-level cap is 2 GiB, but the connected Supabase organization is on the Free plan. The global Free-plan file upload limit is 50 MB, and the effective upload limit is the lower of the global and bucket limits. The application therefore enforces a 50 MiB maximum per file for both source uploads and cloud exports. Larger files are rejected before upload.

Cloudflare R2 is an optional future provider, not required for the current setup. If the account later activates R2, replace the Supabase S3 endpoint, region and credentials with R2 values, verify the bucket, then deliberately raise `MAX_CLOUD_UPLOAD_BYTES`. The storage adapter remains provider-neutral, so the editor and rendering pipeline do not need to be rewritten.

## Database
Run the migration release command before serving traffic:
`alembic -c alembic.ini upgrade head`

The application uses the `clipstudio_*` table namespace to avoid collisions with other applications in this Supabase project.

## Verification
- API liveness: `/api/health/live`
- Infrastructure readiness: `/api/health/ready`
- Worker logs must show `analysis.run` registered.
- Upload an authorized test video below 50 MiB, verify upload completion, enqueue analysis, and confirm analysis + clip candidates persist.

Do not mark production-ready until end-to-end upload, worker execution, retries, tenant isolation and result persistence pass.

## Automatic data retention (default policy)

Large binary objects are temporary by default:
- Original uploaded source media: deleted 7 days after upload verification; successful analysis refreshes the expiry to 7 days after analysis completion.
- Cloud exports represented by `ExportedVideo`: deleted when their `expires_at` timestamp is reached. The cleanup worker supports this and preserves the database record. Legacy `/api/render-batch` outputs can be copied to private storage through the authenticated `/api/render-batch/{batch_id}/save-to-cloud?project_id=...` endpoint after completion. The endpoint verifies project ownership and is idempotent. Each export is checked against the active provider's configured file-size cap. The original local files are retained for backward compatibility; local disk cleanup is a separate follow-up.
- Worker temporary files: deleted immediately after each analysis attempt, including failed attempts.
- Analysis metadata, transcript text, clip suggestions and project/editing metadata remain in PostgreSQL; they are comparatively small and preserve useful work.
- Assets with queued or processing analysis jobs are never deleted by the retention sweep.
- Storage deletion is idempotent at the application level: successful deletion clears the object key / records `storage_deleted_at`; failures are logged and retried in the next sweep.

Environment variables:
- `SOURCE_MEDIA_RETENTION_DAYS=7`
- `RETENTION_SWEEP_INTERVAL_SECONDS=900`
- The authenticated legacy export bridge sets `ExportedVideo.expires_at` to `now + EXPORT_RETENTION_DAYS` (default 7 days). Local render files remain until a separate safe local-disk cleanup policy is implemented.

Retention cleanup runs in the dedicated worker; no extra scheduler or local installation is required.
