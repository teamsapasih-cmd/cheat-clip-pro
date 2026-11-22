from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.cloud.rate_limit import (
    consume_auth_limits,
    consume_user_limit,
    enforce_auth_rate_limit,
    enforce_user_rate_limit,
    consume_ip_limit,
    resolve_client_ip,
    enforce_ip_rate_limit,
)


class FakeRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}
        self.keys: list[str] = []

    def eval(self, script, number_of_keys, *args):
        if number_of_keys == 1:
            key, window = args
            self.keys.append(key)
            self.counts[key] = self.counts.get(key, 0) + 1
            return [self.counts[key], int(window)]
        assert number_of_keys == 2
        ip_key, identity_key, window = args
        self.keys.extend([ip_key, identity_key])
        self.counts[ip_key] = self.counts.get(ip_key, 0) + 1
        self.counts[identity_key] = self.counts.get(identity_key, 0) + 1
        return [self.counts[ip_key], self.counts[identity_key], int(window)]


def _request() -> Request:
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/auth/login",
        "raw_path": b"/api/auth/login",
        "query_string": b"",
        "headers": [],
        "client": ("203.0.113.10", 12345),
        "server": ("testserver", 80),
    })


def test_auth_limits_enforce_ip_threshold():
    redis = FakeRedis()
    for _ in range(8):
        assert consume_auth_limits(
            redis,
            action="register",
            client_ip="203.0.113.10",
            identity="person@example.com",
            ip_limit=8,
            identity_limit=20,
            window_seconds=900,
            key_secret="unit-test-secret-that-is-at-least-32-chars",
        ) is None

    assert consume_auth_limits(
        redis,
        action="register",
        client_ip="203.0.113.10",
        identity="another@example.com",
        ip_limit=8,
        identity_limit=20,
        window_seconds=900,
        key_secret="unit-test-secret-that-is-at-least-32-chars",
    ) == 900


def test_identity_limit_is_scoped_to_ip_pair_to_avoid_cross_ip_lockout():
    redis = FakeRedis()
    for ip in ("203.0.113.10", "203.0.113.11"):
        assert consume_auth_limits(
            redis,
            action="login",
            client_ip=ip,
            identity="person@example.com",
            ip_limit=100,
            identity_limit=2,
            window_seconds=900,
            key_secret="unit-test-secret-that-is-at-least-32-chars",
        ) is None

    assert consume_auth_limits(
        redis,
        action="login",
        client_ip="203.0.113.10",
        identity="PERSON@example.com",
        ip_limit=100,
        identity_limit=2,
        window_seconds=900,
        key_secret="unit-test-secret-that-is-at-least-32-chars",
    ) is None
    assert consume_auth_limits(
        redis,
        action="login",
        client_ip="203.0.113.10",
        identity="person@example.com",
        ip_limit=100,
        identity_limit=2,
        window_seconds=900,
        key_secret="unit-test-secret-that-is-at-least-32-chars",
    ) == 900

def test_rate_limit_keys_do_not_store_raw_identity():
    redis = FakeRedis()
    consume_auth_limits(
        redis,
        action="login",
        client_ip="203.0.113.10",
        identity="private@example.com",
        ip_limit=10,
        identity_limit=5,
        window_seconds=900,
        key_secret="unit-test-secret-that-is-at-least-32-chars",
    )
    assert all("private@example.com" not in key for key in redis.keys)
    assert all("203.0.113.10" not in key for key in redis.keys)


def test_auth_rate_limit_fails_closed_when_redis_is_missing(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "true")

    with pytest.raises(HTTPException) as error:
        enforce_auth_rate_limit(_request(), action="login", identity="person@example.com")

    assert error.value.status_code == 503


def test_auth_rate_limit_can_be_disabled_explicitly_for_local_tests(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "false")
    enforce_auth_rate_limit(_request(), action="login", identity="person@example.com")



def test_user_quota_is_atomic_and_hashed():
    redis = FakeRedis()
    kwargs = {
        "action": "analysis.enqueue",
        "user_id": "private-user-id",
        "limit": 2,
        "window_seconds": 900,
        "key_secret": "unit-test-secret-that-is-at-least-32-chars",
    }
    assert consume_user_limit(redis, **kwargs) is None
    assert consume_user_limit(redis, **kwargs) is None
    assert consume_user_limit(redis, **kwargs) == 900
    assert all("private-user-id" not in key for key in redis.keys)


def test_user_quota_rejects_unknown_actions():
    with pytest.raises(ValueError):
        consume_user_limit(
            FakeRedis(),
            action="unknown",
            user_id="user-1",
            limit=1,
            window_seconds=60,
            key_secret="unit-test-secret-that-is-at-least-32-chars",
        )



def test_user_rate_limit_fails_closed_when_redis_is_missing(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-secret-that-is-at-least-32-chars")

    with pytest.raises(HTTPException) as error:
        enforce_user_rate_limit(
            action="analysis.enqueue",
            user_id="user-1",
            limit=3,
            window_seconds=900,
        )

    assert error.value.status_code == 503


def test_user_rate_limit_can_be_disabled_for_local_tests(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "false")
    enforce_user_rate_limit(
        action="analysis.enqueue",
        user_id="user-1",
        limit=3,
        window_seconds=900,
    )



def test_railway_client_ip_uses_only_x_real_ip_for_matching_public_host(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "testserver")
    request = _request()
    request.scope["headers"] = [(b"host", b"testserver"), (b"x-real-ip", b"198.51.100.42")]
    assert resolve_client_ip(request) == "198.51.100.42"


def test_railway_client_ip_does_not_trust_forwarded_for(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "testserver")
    request = _request()
    request.scope["headers"] = [(b"host", b"testserver"), (b"x-forwarded-for", b"198.51.100.42")]
    with pytest.raises(HTTPException) as error:
        resolve_client_ip(request)
    assert error.value.status_code == 503


def test_railway_client_ip_rejects_wrong_host_and_invalid_ip(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "public.example")
    with pytest.raises(HTTPException):
        resolve_client_ip(_request())

    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "testserver")
    request = _request()
    request.scope["headers"] = [(b"host", b"testserver"), (b"x-real-ip", b"not-an-ip")]
    with pytest.raises(HTTPException):
        resolve_client_ip(request)


def test_local_client_ip_uses_direct_peer_not_forwarded_header(monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    request = _request()
    request.scope["headers"] = [(b"host", b"testserver"), (b"x-forwarded-for", b"198.51.100.42")]
    assert resolve_client_ip(request) == "203.0.113.10"


def test_ip_quota_is_atomic_hashed_and_action_scoped():
    redis = FakeRedis()
    kwargs = {
        "action": "legacy.analyze",
        "client_ip": "198.51.100.42",
        "limit": 2,
        "window_seconds": 900,
        "key_secret": "unit-test-secret-that-is-at-least-32-chars",
    }
    assert consume_ip_limit(redis, **kwargs) is None
    assert consume_ip_limit(redis, **kwargs) is None
    assert consume_ip_limit(redis, **kwargs) == 900
    assert all("198.51.100.42" not in key for key in redis.keys)


def test_ip_quota_rejects_unknown_actions():
    with pytest.raises(ValueError):
        consume_ip_limit(
            FakeRedis(),
            action="unknown",
            client_ip="198.51.100.42",
            limit=1,
            window_seconds=60,
            key_secret="unit-test-secret-that-is-at-least-32-chars",
        )


def test_ip_rate_limit_fails_closed_without_railway_edge_identity(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "testserver")
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-secret-that-is-at-least-32-chars")
    request = _request()
    with pytest.raises(HTTPException) as error:
        enforce_ip_rate_limit(request, action="legacy.analyze", limit=5)
    assert error.value.status_code == 503
