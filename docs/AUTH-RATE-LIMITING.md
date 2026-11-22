# Distributed rate-limit deployment notes

Sensitive authentication and cloud-work endpoints use atomic Redis counters shared by all API replicas. Raw email addresses, client IP addresses, and account IDs are transformed with keyed HMAC-SHA256 before they are used in Redis keys. The authentication identity counter is scoped to the IP/email pair (not globally to the email), so one visitor cannot lock an account out for every other visitor. Account quotas use a separate per-user digest. The HMAC key is read from `AUTH_RATE_LIMIT_KEY` when configured, otherwise from the existing `JWT_SECRET_KEY`; it must be at least 32 characters. Keep either secret private and stable across API replicas.

## Defaults

| Endpoint | Scope | Limit | Window |
| --- | --- | ---: | ---: |
| `POST /api/auth/register` | client IP | 8 attempts | 15 minutes |
| `POST /api/auth/register` | client IP + normalized email | 3 attempts | 15 minutes |
| `POST /api/auth/login` | client IP | 20 attempts | 15 minutes |
| `POST /api/auth/login` | client IP + normalized email | 10 attempts | 15 minutes |
| `POST /api/analyses` | authenticated user | 3 jobs | 15 minutes |
| `POST /api/media/cloud/upload-intent` | authenticated user | 10 intents | 15 minutes |

Rejected requests return HTTP 429 and a `Retry-After` header. If rate limiting is enabled but Redis is not configured or cannot be reached, protected endpoints return HTTP 503 (fail-closed behavior). Account quotas count attempts before downstream validation, preventing repeated invalid requests from avoiding the quota.

## Required deployment configuration

- Set `REDIS_URL` to the deployment's private Redis connection URL.
- Keep `AUTH_RATE_LIMIT_ENABLED=true` (the default).
- Do not set `AUTH_RATE_LIMIT_ENABLED=false` in a public deployment. That switch exists for isolated local tests only.
- Ensure Redis is reachable from every API replica and that its keys are not evicted before their TTL expires.
- Configure the ASGI server's trusted proxy handling correctly before relying on `request.client.host` as the visitor IP. Do not trust arbitrary `X-Forwarded-For` headers from untrusted clients.

## Verification

Run:

```bash
python -m pytest -q tests/test_auth_rate_limit.py tests/test_auth_api.py tests/test_analysis_jobs_api.py
```

The unit tests verify IP and IP/email-pair thresholds, normalized email matching, hashed Redis key identifiers, per-user quotas, explicit local-test disablement, and fail-closed behavior when Redis is missing. The tests use a fake Redis implementation; they do not replace a staging test against the actual deployment Redis service.

## Remaining scope

Legacy unauthenticated media upload, source processing, audio extraction, frame/face analysis, render, retry, and download routes do not yet have endpoint quotas. IP-based protection for those routes remains blocked on verified trusted-proxy configuration to avoid treating a shared proxy address as every visitor. Email verification and account recovery are also separate unfinished authentication requirements.
