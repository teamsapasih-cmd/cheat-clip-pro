from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.cloud.rate_limit import consume_auth_limits, enforce_auth_rate_limit


class FakeRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}
        self.keys: list[str] = []

    def eval(self, script, number_of_keys, *args):
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
