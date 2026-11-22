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
| `POST /api/analyze` | visitor IP | 5 requests | 15 minutes |
| `POST /api/upload-video` | visitor IP | 8 uploads | 15 minutes |
| `POST /api/transcribe-clip-words` | visitor IP | 20 requests | 15 minutes |
| `POST /api/render-batch` | visitor IP | 6 jobs | 15 minutes |
| `POST /api/render-batch/{id}/retry` | visitor IP | 4 retries | 15 minutes |
| `POST /api/prepare-source` | visitor IP | 8 jobs | 15 minutes |
| `POST /api/download-raw-video` | visitor IP | 3 jobs | 15 minutes |
| `POST /api/download-raw-clip` | visitor IP | 12 jobs | 15 minutes |
| BGM/SFX/watermark/font uploads | visitor IP (shared bucket) | 30 uploads | 15 minutes |

All counters are atomic Redis increments with expiry and action-specific keys. Rejected requests return HTTP 429 with a `Retry-After` header. If rate limiting is enabled but Redis is not configured or cannot be reached, protected endpoints return HTTP 503 (fail-closed behavior). Invalid requests count toward the quota once the route handler begins.

## Railway client-IP trust

The production API is behind Railway's HTTP edge. Railway identifies the environment through `RAILWAY_ENVIRONMENT_NAME` (not `RAILWAY_ENVIRONMENT`), and provides `RAILWAY_PUBLIC_DOMAIN` for the service hostname. Railway's public-networking documentation identifies `X-Real-IP` as the request header for the client's remote IP. The application reads only this header in Railway, validates it as an IP address, and accepts it only when the request host exactly matches the service's `RAILWAY_PUBLIC_DOMAIN`. It does not trust `X-Forwarded-For`. Outside Railway, tests and local development use the direct ASGI peer address.

This application-level resolver is intentional: the current Railway start command does not configure Uvicorn's forwarded-header trust list, and we do not need to enable broad forwarded-header trust to use Railway's documented client-IP header. If the Railway public domain or `X-Real-IP` is absent or invalid, protected IP-based routes fail closed with HTTP 503 instead of falling back to the shared proxy address.

Railway reference: [Public networking specs and limits](https://docs.railway.com/networking/public-networking/specs-and-limits).

## Required deployment configuration

- Set `REDIS_URL` to the deployment's private Redis connection URL.
- Keep `AUTH_RATE_LIMIT_ENABLED=true` (the default).
- Do not set `AUTH_RATE_LIMIT_ENABLED=false` in a public deployment. That switch exists for isolated local tests only.
- Ensure Redis is reachable from every API replica and that its keys are not evicted before their TTL expires.
- Keep `RAILWAY_PUBLIC_DOMAIN` supplied by Railway. Do not replace it with a manually entered host or trust arbitrary forwarded headers.
- Do not add Uvicorn `--forwarded-allow-ips=*` or trust all proxy headers as a shortcut.

## Important behavior and limitations

- The legacy endpoints remain unauthenticated. Their quotas are per visitor IP; users sharing a public IP (for example, some mobile carrier or school networks) share the quota for the same operation. Limits are deliberately endpoint-specific and conservative.
- Cloud analysis and upload-intent endpoints use authenticated per-account quotas instead of visitor-IP quotas.
- FastAPI parses multipart upload bodies before entering the endpoint function. These handler quotas prevent repeated file processing/storage work, but they are not an ingress bandwidth firewall. Use platform edge/network controls for volumetric traffic or oversized request-body protection.
- Polling/status endpoints and ordinary media GETs are not included in this first quota pass to avoid breaking normal progress polling, video playback, and browser range requests.
- IP quotas do not replace account authentication, ownership checks, object-level authorization, upload-size validation, or edge DDoS protection.

## Verification

Run:

```bash
python -m pytest -q tests/test_auth_rate_limit.py tests/test_auth_api.py tests/test_analysis_jobs_api.py
```

Tests cover IP and IP/email-pair thresholds, normalized email matching, HMAC-hashed identifiers, per-user and per-IP quotas, trusted Railway `X-Real-IP` handling, rejection of `X-Forwarded-For`-only requests, host/IP validation, explicit local-test disablement, and fail-closed behavior. They use a fake Redis implementation; they do not replace an end-to-end check through the live Railway edge and actual Redis service.

## Remaining release gates

- Verify through a controlled non-production request that Railway supplies the expected `X-Real-IP` value and the public host matches `RAILWAY_PUBLIC_DOMAIN`; do not log or expose a visitor's raw IP.
- Verify the real Redis counter behavior and HTTP 429/503 responses in staging.
- Add edge-level body-size and volumetric protections where supported by the plan.
- Email verification and credential recovery remain separate unfinished authentication requirements.
