import pytest

from backend.cloud.settings import CloudSettings, validate_production_configuration


def test_empty_environment_reports_missing_components():
    settings = CloudSettings.from_env({})
    assert settings.infrastructure_configured is False
    assert "DATABASE_URL" in settings.missing_components()
    assert "REDIS_URL" in settings.missing_components()
    assert "OBJECT_STORAGE_BUCKET" in settings.missing_components()


def test_complete_environment_is_recognized_without_connecting():
    env = {
        "DATABASE_URL": "postgresql://user:pass@example.invalid/app",
        "REDIS_URL": "redis://example.invalid:6379/0",
        "OBJECT_STORAGE_ENDPOINT": "https://storage.example.invalid",
        "OBJECT_STORAGE_BUCKET": "private-media",
        "OBJECT_STORAGE_ACCESS_KEY": "test-access",
        "OBJECT_STORAGE_SECRET_KEY": "test-secret",
    }
    settings = CloudSettings.from_env(env)
    assert settings.infrastructure_configured is True
    assert settings.missing_components() == ()


def test_strict_mode_fails_with_names_only_and_no_secret_values():
    env = {
        "CLOUD_REQUIRE_INFRASTRUCTURE": "true",
        "OBJECT_STORAGE_SECRET_KEY": "do-not-leak-this",
    }
    with pytest.raises(RuntimeError) as error:
        validate_production_configuration(env)

    assert "DATABASE_URL" in str(error.value)
    assert "do-not-leak-this" not in str(error.value)


def test_strict_mode_is_opt_in():
    validate_production_configuration({})
