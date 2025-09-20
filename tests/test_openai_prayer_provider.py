"""Tests for the OpenAI prayer generation provider."""

import pytest
from unittest.mock import Mock, patch

from app_helpers.services.ai_providers.base import PrayerGenerationError
from app_helpers.services.ai_providers.config import AIProviderConfig
from app_helpers.services.ai_providers.openai_provider import OpenAIPrayerProvider


def _make_config(**overrides):
    data = {
        "provider": "openai",
        "anthropic_api_key": None,
        "openai_api_key": "sk-test",
        "openai_model": "gpt-test",
        "openai_api_base": None,
    }
    data.update(overrides)
    return AIProviderConfig(**data)


def test_generate_prayer_success():
    config = _make_config()

    mock_client = Mock()
    mock_response = Mock()
    mock_response.output_text = "Test prayer"
    mock_client.responses.create.return_value = mock_response

    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))

    with patch('app_helpers.services.ai_providers.openai_provider.importlib.import_module', return_value=mock_openai_module) as mock_import:
        provider = OpenAIPrayerProvider(config)
        result = provider.generate_prayer(
            "Please pray",
            system_prompt="system",
            max_tokens=150,
            temperature=0.3,
        )

    mock_import.assert_called_once_with("openai")
    mock_openai_module.OpenAI.assert_called_once_with(api_key="sk-test")
    mock_client.responses.create.assert_called_once()
    args, kwargs = mock_client.responses.create.call_args
    assert kwargs["model"] == "gpt-test"
    assert kwargs["max_output_tokens"] == 150
    assert kwargs["temperature"] == 0.3
    assert kwargs["input"][0]["role"] == "system"
    assert kwargs["input"][1]["role"] == "user"

    assert result.text == "Test prayer"
    assert result.provider == "openai"


def test_generate_prayer_respects_custom_base_url():
    config = _make_config(openai_api_base="https://example.test/v1")

    mock_client = Mock()
    mock_client.responses.create.return_value = Mock(output_text="text")
    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))

    with patch('app_helpers.services.ai_providers.openai_provider.importlib.import_module', return_value=mock_openai_module) as mock_import:
        provider = OpenAIPrayerProvider(config)
        provider.generate_prayer("Prompt", system_prompt="sys", max_tokens=100)

    mock_import.assert_called_once_with("openai")
    mock_openai_module.OpenAI.assert_called_once_with(api_key="sk-test", base_url="https://example.test/v1")


def test_generate_prayer_handles_nested_output_structure():
    config = _make_config()

    mock_client = Mock()

    class Block:
        def __init__(self, text):
            self.text = text

    class OutputItem:
        def __init__(self, content):
            self.content = content

    mock_response = Mock(output=[OutputItem([Block("Nested prayer")])])
    mock_response.output_text = None
    mock_client.responses.create.return_value = mock_response

    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))

    with patch('app_helpers.services.ai_providers.openai_provider.importlib.import_module', return_value=mock_openai_module):
        provider = OpenAIPrayerProvider(config)
        result = provider.generate_prayer("Prompt", system_prompt="sys", max_tokens=100)

    assert result.text == "Nested prayer"


def test_generate_prayer_wraps_errors():
    config = _make_config()

    mock_client = Mock()
    mock_client.responses.create.side_effect = Exception("Boom")

    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))

    with patch('app_helpers.services.ai_providers.openai_provider.importlib.import_module', return_value=mock_openai_module):
        provider = OpenAIPrayerProvider(config)
        with pytest.raises(PrayerGenerationError) as exc:
            provider.generate_prayer("Prompt", system_prompt="sys", max_tokens=50)

    assert "Boom" in str(exc.value)


def test_missing_api_key_raises():
    config = _make_config(openai_api_key=None)
    with pytest.raises(PrayerGenerationError):
        OpenAIPrayerProvider(config)
