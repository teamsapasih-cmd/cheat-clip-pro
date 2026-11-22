# Authentication rate-limit deployment notes

The registration and login endpoints use atomic Redis counters shared by all API
replicas. Raw email addresses and client IP addresses are transformed with keyed HMAC-SHA256
before they are used in Redis keys. The identity counter is scoped to the IP/email pair (not globally to the email), so one visitor cannot lock an account out for every other visitor. The HMAC key is read from `AUTH_RATE_LIMIT_KEY`
when configured, otherwise from the existing `JWT_SECRET_KEY`; it must be at
least 32 characters. Keep either secret private and stable across API replicas.

## Defaults

| Endpoint | Per client IP | Per client IP + normalized email | Window |
| --- | ---: | ---: | ---: |
| `POST /api/auth/register` | 8 attempts | 3 attempts | 15 minutes |
| `POST /api/auth/login` | 20 attempts | 10 attempts | 15 minutes |

A rejected request returns HTTP 429 and a `Retry-After` header. If rate limiting
is enabled but Redis is not configured or cannot be reached, the auth endpoint
returns HTTP 503 (fail-closed behavior).

## Required deployment configuration

- Set `REDIS_URL` to the deployment's private Redis connection URL.
- Keep `AUTH_RATE_LIMIT_ENABLED=true` (the default).
- Do not set `AUTH_RATE_LIMIT_ENABLED=false` in a public deployment. That switch
  exists for isolated local tests only.
- Ensure Redis is reachable from every API replica and that its keys are not
  evicted before their TTL expires.
- Configure the ASGI server's trusted proxy handling correctly before relying
  on `request.client.host` as the visitor IP. Do not trust arbitrary
  `X-Forwarded-For` headers from untrusted clients.

## Verification

Run:

```bash
python -m pytest -q tests/test_auth_rate_limit.py tests/test_auth_api.py
```

The unit tests verify IP and IP/email-pair thresholds, normalized email matching,
hashed Redis key identifiers, explicit local-test disablement, and fail-closed
behavior when Redis is missing. Redis identifiers use keyed digests and are
never stored as raw email addresses or IPs. The tests use a fake Redis implementation; they do
not replace a staging test against the actual deployment Redis service.

## Scope and remaining work

This protects registration and login only. It does not yet impose quotas on
legacy analysis, source-download, upload, render, or transcription routes.
Those routes need separate endpoint-specific budgets and a verified proxy/IP
trust configuration before public exposure. Email verification and account
recovery are also separate unfinished authentication requirements.
