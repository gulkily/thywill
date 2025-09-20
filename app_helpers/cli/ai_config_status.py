"""CLI helper to display AI provider configuration status."""

from __future__ import annotations

from app_helpers.services.ai_providers import (
    AIConfigurationError,
    get_ai_provider_config,
    validate_ai_provider_config,
)


def main() -> None:
    print("AI Provider Configuration:")
    try:
        config = get_ai_provider_config()
    except AIConfigurationError as exc:
        print(f"  Provider: invalid ({exc})")
        return

    print(f"  Provider: {config.provider}")
    if config.using_anthropic:
        print(f"  Anthropic key set: {'yes' if config.anthropic_api_key else 'no'}")
    if config.using_openai or config.openai_api_key:
        print(f"  OpenAI key set: {'yes' if config.openai_api_key else 'no'}")
        print(f"  OpenAI model: {config.openai_model}")
        if config.openai_api_base:
            print(f"  OpenAI API base: {config.openai_api_base}")

    is_valid, error_message = validate_ai_provider_config(raise_error=False)
    status = "OK" if is_valid else f"ERROR - {error_message}"
    print(f"  Status: {status}")


if __name__ == "__main__":
    main()
