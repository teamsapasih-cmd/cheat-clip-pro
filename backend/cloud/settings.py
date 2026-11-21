"""Safe, provider-neutral cloud configuration.

This module reads environment variables but never logs or returns secret values.
Partial configuration is allowed during local development; production validation
can be enabled explicitly with CLOUD_REQUIRE_INFRASTRUCTURE=1.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class CloudSettings:
    database_url: str | None
    redis_url: str | None
    object_storage_endpoint: str | None
    object_storage_bucket: str | None
    object_storage_access_key: str | None
    object_storage_secret_key: str | None
    object_storage_region: str | None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "CloudSettings":
        source = os.environ if env is None else env

        def value(name: str) -> str | None:
            raw = source.get(name, "").strip()
            return raw or None

        return cls(
            database_url=value("DATABASE_URL"),
            redis_url=value("REDIS_URL"),
            object_storage_endpoint=value("OBJECT_STORAGE_ENDPOINT"),
            object_storage_bucket=value("OBJECT_STORAGE_BUCKET"),
            object_storage_access_key=value("OBJECT_STORAGE_ACCESS_KEY"),
            object_storage_secret_key=value("OBJECT_STORAGE_SECRET_KEY"),
            object_storage_region=value("OBJECT_STORAGE_REGION"),
        )

    def missing_components(self) -> tuple[str, ...]:
        missing: list[str] = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.redis_url:
            missing.append("REDIS_URL")

        storage_required = {
            "OBJECT_STORAGE_ENDPOINT": self.object_storage_endpoint,
            "OBJECT_STORAGE_BUCKET": self.object_storage_bucket,
            "OBJECT_STORAGE_ACCESS_KEY": self.object_storage_access_key,
            "OBJECT_STORAGE_SECRET_KEY": self.object_storage_secret_key,
        }
        missing.extend(name for name, configured in storage_required.items() if not configured)
        return tuple(missing)

    @property
    def infrastructure_configured(self) -> bool:
        return not self.missing_components()


def validate_production_configuration(env: Mapping[str, str] | None = None) -> None:
    """Fail fast only when an operator explicitly enables strict cloud mode."""
    source = os.environ if env is None else env
    strict = source.get("CLOUD_REQUIRE_INFRASTRUCTURE", "").strip().lower()
    if strict not in {"1", "true", "yes"}:
        return

    missing = list(CloudSettings.from_env(source).missing_components())
    jwt_secret = source.get("JWT_SECRET_KEY", "").strip()
    if len(jwt_secret) < 32:
        missing.append("JWT_SECRET_KEY (minimum 32 characters)")
    if not (source.get("GEMINI_API_KEY", "").strip() or source.get("OPENROUTER_API_KEY", "").strip()):
        missing.append("GEMINI_API_KEY or OPENROUTER_API_KEY")
    if missing:
        raise RuntimeError(
            "Cloud infrastructure configuration is incomplete. Missing: "
            + ", ".join(missing)
        )
