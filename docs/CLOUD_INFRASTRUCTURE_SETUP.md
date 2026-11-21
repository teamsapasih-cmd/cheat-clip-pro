# Cloud infrastructure setup

This repository now has a provider-neutral foundation for cloud services. It does
not connect to or provision paid services automatically.

## Required deployment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string for durable background jobs |
| `OBJECT_STORAGE_ENDPOINT` | S3-compatible object-storage endpoint |
| `OBJECT_STORAGE_BUCKET` | Private media bucket name |
| `OBJECT_STORAGE_ACCESS_KEY` | Storage service access key |
| `OBJECT_STORAGE_SECRET_KEY` | Storage service secret |
| `OBJECT_STORAGE_REGION` | Optional storage region |

The application reads these values through `backend.cloud.settings.CloudSettings`.
It reports missing variable names only; it never returns secret values.

## Strict production validation

Set `CLOUD_REQUIRE_INFRASTRUCTURE=1` only after all services and secrets have
been configured in the deployment platform. The validation helper then fails
fast and lists missing variable names. Strict mode is opt-in so existing local
and current deployments are not broken.

## Adapter implementation sequence

1. PostgreSQL repository and migrations.
2. Redis-backed durable job queue and independent worker process.
3. Private S3-compatible media storage with signed upload/download URLs.
4. Per-user authorization and tenant-scoped media/job records.
5. Migration of existing local render/download workflows behind the new contracts.

Do not place service credentials in source files, browser JavaScript, commit
messages, or chat. Configure them in the cloud provider's secret/environment
settings. Use private buckets and short-lived signed URLs.

## Current limitation

The contracts and configuration are scaffolding only. No database, Redis, or
object-storage network client is instantiated yet. Existing local filesystem
processing remains the active implementation until adapters are implemented,
tested, and deployed.
