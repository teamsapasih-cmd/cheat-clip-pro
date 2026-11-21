import pytest

from backend.auth.tokens import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_verifies_and_is_not_plaintext():
    encoded = hash_password("a-long-test-password")
    assert encoded != "a-long-test-password"
    assert verify_password("a-long-test-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_password_policy_rejects_short_password():
    with pytest.raises(ValueError):
        hash_password("short")


def test_access_token_round_trip(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-that-is-at-least-thirty-two-characters")
    token = create_access_token("user-123", expires_minutes=10)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_token_requires_strong_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "weak")
    with pytest.raises(RuntimeError):
        create_access_token("user-123")
    assert decode_access_token("invalid") is None
