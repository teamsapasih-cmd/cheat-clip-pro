# Cloud infrastructure setup

This repository uses provider-neutral adapters. The current no-card storage configuration uses the existing private Supabase Storage bucket; Cloudflare R2 is optional and is not required.

## Required deployment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `REDIS_URL` | Redis connection string for durable background jobs |
| `OBJECT_STORAGE_ENDPOINT` | Supabase S3-compatible endpoint |
| `OBJECT_STORAGE_BUCKET` | Private Supabase Storage bucket |
| `OBJECT_STORAGE_ACCESS_KEY` | Supabase server-side S3 access key |
| `OBJECT_STORAGE_SECRET_KEY` | Supabase server-side S3 secret |
| `OBJECT_STORAGE_REGION` | Region shown in Supabase S3 settings |
| `MAX_CLOUD_UPLOAD_BYTES` | 52428800 (50 MiB on Supabase Free) |

Generate S3 credentials in Supabase Dashboard > Storage > Configuration > S3. These credentials provide broad access to Storage and bypass Storage RLS. They are server-only secrets; never put them in browser variables, source files, or chat.

## Current free-tier limit

The existing private bucket is named `clipstudio-private-media`. Its bucket-level cap is 2 GiB, but the Supabase Free global upload cap is 50 MB. The app enforces a conservative 50 MiB per-file limit for source uploads and cloud exports. Files larger than this are rejected before transfer. This limit can only be raised after selecting and configuring a provider/plan that supports the larger files.

## Optional future Cloudflare R2

R2 is deliberately not required now. If it is activated later, replace the endpoint, region and S3 credentials with the R2 values and increase `MAX_CLOUD_UPLOAD_BYTES` only after verifying the R2 bucket and account billing configuration. The S3 adapter stays the same, so application workflows remain portable.

## Strict production validation

Keep `CLOUD_REQUIRE_INFRASTRUCTURE=0` while the free-tier services are being assembled. Set it to `1` only after PostgreSQL, Redis, object storage, JWT and AI provider credentials are configured in the deployment platform. The validation helper fails fast and lists missing variable names without exposing secret values.

## Adapter implementation sequence

1. PostgreSQL repository and migrations.
2. Redis-backed durable job queue and independent worker process.
3. Private S3-compatible media storage with signed upload/download URLs.
4. Per-user authorization and tenant-scoped media/job records.
5. Migration of existing local render/download workflows behind the new contracts.

Use private buckets and short-lived signed URLs. Do not mark production-ready until end-to-end upload, worker execution, retries, tenant isolation and result persistence pass.
