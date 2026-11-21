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
- `OBJECT_STORAGE_ENDPOINT`: `https://luelliccbrgwlrkdfhrw.supabase.co/storage/v1/s3`
- `OBJECT_STORAGE_REGION`: `ap-south-1`
- `OBJECT_STORAGE_BUCKET`: `clipstudio-private-media`
- `OBJECT_STORAGE_ACCESS_KEY` and `OBJECT_STORAGE_SECRET_KEY`: generated under Supabase Dashboard → Storage → S3 Configuration → Access keys.
- `JWT_SECRET_KEY`: long random secret (at least 32 random bytes).
- `GEMINI_API_KEY`: provider key for the worker, unless the request uses OpenRouter.
- `CLOUD_REQUIRE_INFRASTRUCTURE`: `1`
- `MAX_CLOUD_UPLOAD_BYTES`: `2147483648`
- `ALLOWED_ORIGINS`: deployed web origin. If the frontend is served by this API, use that same origin.

Never commit real values or send credentials in chat. Configure secrets only in the hosting provider Variables UI.

## Storage
A private bucket `clipstudio-private-media` exists in Supabase Storage. It is limited to 2 GiB per object and the MIME types accepted by the upload API. S3 access keys are separate from Supabase publishable/anon keys.

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
