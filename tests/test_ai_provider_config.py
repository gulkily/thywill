"""Tests for AI provider configuration helpers."""

import os

import pytest

from app_helpers.services.ai_providers import (
    AIConfigurationError,
    get_ai_provider_config,
    validate_ai_provider_config,
)


AI_ENV_VARS = {
    "AI_PROVIDER",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_API_BASE",
}


@pytest.fixture(autouse=True)
def clear_ai_env(monkeypatch):
    """Ensure AI-related env vars are cleared before each test."""
    for env_var in AI_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
    yield
    for env_var in AI_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


def test_default_anthropic_configuration(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    config = get_ai_provider_config()

    assert config.provider == "anthropic"
    assert config.using_anthropic
    assert config.anthropic_api_key == "test-anthropic"

    valid, error = validate_ai_provider_config(raise_error=False)
    assert valid
    assert error is None


def test_invalid_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "invalid-provider")
    valid, error = validate_ai_provider_config(raise_error=False)

    assert not valid
    assert "Unsupported AI provider" in error
    with pytest.raises(AIConfigurationError):
        get_ai_provider_config()


def test_anthropic_requires_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")

    valid, error = validate_ai_provider_config(raise_error=False)
    assert not valid
    assert "ANTHROPIC_API_KEY" in error


def test_openai_requires_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")

    valid, error = validate_ai_provider_config(raise_error=False)
    assert not valid
    assert "OPENAI_API_KEY" in error


def test_openai_configuration(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("OPENAI_API_BASE", "https://example.test/v1")

    config = get_ai_provider_config()

    assert config.provider == "openai"
    assert config.using_openai
    assert config.openai_api_key == "sk-test"
    assert config.openai_model == "gpt-test"
    assert config.openai_api_base == "https://example.test/v1"

    valid, error = validate_ai_provider_config(raise_error=False)
    assert valid
    assert error is None
