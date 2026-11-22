"""Redis-backed rate limiting for sensitive authentication endpoints.

Counters are shared across API replicas. If enforcement is enabled but Redis is
unavailable, requests fail closed with 503 rather than silently losing limits.
"""
from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError


_INCREMENT_TWO_KEYS = """
local ip_count = redis.call('INCR', KEYS[1])
if ip_count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local identity_count = redis.call('INCR', KEYS[2])
if identity_count == 1 then redis.call('EXPIRE', KEYS[2], ARGV[1]) end
local ip_ttl = redis.call('TTL', KEYS[1])
local identity_ttl = redis.call('TTL', KEYS[2])
return {ip_count, identity_count, math.max(ip_ttl, identity_ttl)}
"""


def _digest(value: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def consume_auth_limits(
    redis_client: Redis,
    *,
    action: str,
    client_ip: str,
    identity: str,
    ip_limit: int,
    identity_limit: int,
    window_seconds: int,
    key_secret: str,
) -> int | None:
    """Increment IP and normalized-identity counters atomically.

    Returns the retry delay when either threshold is exceeded, otherwise None.
    Raw email addresses and IPs are never stored in Redis key names.
    """
    if action not in {"register", "login"}:
        raise ValueError("Unsupported authentication rate-limit action")
    if min(ip_limit, identity_limit, window_seconds) < 1:
        raise ValueError("Rate-limit values must be positive")
    if len(key_secret) < 32:
        raise ValueError("Rate-limit key secret must contain at least 32 characters")

    prefix = f"clipstudio:ratelimit:auth:{action}"
    keys = [
        f"{prefix}:ip:{_digest(client_ip, key_secret)}",
        f"{prefix}:identity-ip:{_digest(client_ip + chr(0) + identity.strip().lower(), key_secret)}",
    ]
    result = redis_client.eval(_INCREMENT_TWO_KEYS, 2, *keys, window_seconds)
    ip_count, identity_count, ttl = (int(value) for value in result)
    if ip_count > ip_limit or identity_count > identity_limit:
        return max(1, ttl)
    return None


def enforce_auth_rate_limit(request: Request, *, action: str, identity: str) -> None:
    """Apply a distributed auth limit; fail closed if enabled Redis is unavailable."""
    enabled = os.environ.get("AUTH_RATE_LIMIT_ENABLED", "true").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return

    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication protection is temporarily unavailable",
        )

    key_secret = os.environ.get("AUTH_RATE_LIMIT_KEY", "").strip() or os.environ.get("JWT_SECRET_KEY", "").strip()
    if len(key_secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication protection is temporarily unavailable",
        )

    limits = {
        "register": (8, 3, 900),
        "login": (20, 10, 900),
    }
    if action not in limits:
        raise ValueError("Unsupported authentication rate-limit action")
    ip_limit, identity_limit, window_seconds = limits[action]
    client_ip = request.client.host if request.client else "unknown"

    try:
        client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            retry_after = consume_auth_limits(
                client,
                action=action,
                client_ip=client_ip,
                identity=identity,
                ip_limit=ip_limit,
                identity_limit=identity_limit,
                window_seconds=window_seconds,
                key_secret=key_secret,
            )
        finally:
            client.close()
    except (RedisError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication protection is temporarily unavailable",
        ) from exc

    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please wait before trying again.",
            headers={"Retry-After": str(retry_after)},
        )


_USER_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""


def consume_user_limit(
    redis_client: Redis,
    *,
    action: str,
    user_id: str,
    limit: int,
    window_seconds: int,
    key_secret: str,
) -> int | None:
    """Apply an atomic per-account quota without storing the raw account ID."""
    if action not in {"analysis.enqueue", "media.upload_intent"}:
        raise ValueError("Unsupported user rate-limit action")
    if min(limit, window_seconds) < 1:
        raise ValueError("Rate-limit values must be positive")
    if len(key_secret) < 32:
        raise ValueError("Rate-limit key secret must contain at least 32 characters")

    digest = _digest(user_id.strip(), key_secret)
    key = f"clipstudio:ratelimit:user:{action}:{digest}"
    count, ttl = (int(value) for value in redis_client.eval(
        _USER_LIMIT_SCRIPT, 1, key, window_seconds
    ))
    return max(1, ttl) if count > limit else None


def enforce_user_rate_limit(
    *,
    action: str,
    user_id: str,
    limit: int,
    window_seconds: int = 900,
) -> None:
    """Enforce a distributed quota for an authenticated account; fail closed."""
    enabled = os.environ.get("AUTH_RATE_LIMIT_ENABLED", "true").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return

    redis_url = os.environ.get("REDIS_URL", "").strip()
    key_secret = (
        os.environ.get("AUTH_RATE_LIMIT_KEY", "").strip()
        or os.environ.get("JWT_SECRET_KEY", "").strip()
    )
    if not redis_url or len(key_secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Request protection is temporarily unavailable",
        )

    try:
        client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            retry_after = consume_user_limit(
                client,
                action=action,
                user_id=user_id,
                limit=limit,
                window_seconds=window_seconds,
                key_secret=key_secret,
            )
        finally:
            client.close()
    except (RedisError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Request protection is temporarily unavailable",
        ) from exc

    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Request quota exceeded. Please wait before trying again.",
            headers={"Retry-After": str(retry_after)},
        )
