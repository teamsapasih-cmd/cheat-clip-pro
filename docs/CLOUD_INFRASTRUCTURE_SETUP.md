# Cloud infrastructure setup

## Active storage configuration

Use the existing private Supabase Storage bucket `clipstudio-private-media`. S3 protocol is enabled and the dashboard shows an access key named `clipping`.

| Variable | Value |
| --- | --- |
| `OBJECT_STORAGE_ENDPOINT` | `https://luelliccbrgwlrkdfhrw.storage.supabase.co/storage/v1/s3` |
| `OBJECT_STORAGE_REGION` | `ap-south-1` |
| `OBJECT_STORAGE_BUCKET` | `clipstudio-private-media` |
| `OBJECT_STORAGE_ACCESS_KEY` | Access Key ID from key `clipping` |
| `OBJECT_STORAGE_SECRET_KEY` | Matching Secret Access Key |

The screenshot confirms the S3 connection is enabled and the key ID exists. It does not show the secret key. Supabase only shows the secret when the key is created. If it was not saved, create a replacement key, store its secret directly in Railway Variables, verify connectivity, then revoke the old key.

S3 credentials are server-side secrets. Never put them in browser code, Git or chat.

## Free-plan upload limit

The bucket-level cap is 2 GiB, but Supabase Free's global per-file upload limit is 50 MB. Set `MAX_CLOUD_UPLOAD_BYTES=50000000` (decimal 50 MB) and reject larger files before transfer. Do not claim support for multi-gigabyte uploads on this configuration.

## Railway services still to configure

- API/web service: deploy the application from branch `clip-intelligence-upgrade`.
- Worker service: same image, start command `python -m backend.workers.redis_worker`.
- Redis: provision a Redis service and set `REDIS_URL`.
- Supabase PostgreSQL: set `DATABASE_URL`.
- JWT and AI provider secrets: set `JWT_SECRET_KEY` and `GEMINI_API_KEY` or `OPENROUTER_API_KEY`.
- Keep `CLOUD_REQUIRE_INFRASTRUCTURE=0` until all infrastructure is configured and tested.

## Optional R2 migration

R2 remains optional and is not required now. If activated in future, replace the S3 endpoint, region, bucket and credentials, then deliberately update the file-size limit based on the actual plan. The S3 adapter remains provider-neutral.
