# OpenAI Backend Support - Step 2 Feature Description

## Problem
Prayer generation currently depends on Anthropic only, blocking environments without that key and creating a single point of failure.

## User Stories
- As a developer, I want to choose OpenAI or Anthropic via configuration so deployments can match available credentials.
- As a prayer leader, I want generated prayers to remain consistent regardless of provider so quality and tone stay intact.
- As an operator, I want clear telemetry and fallback rules so the system gracefully handles provider errors.

## Core Requirements
- Add env/CLI configuration to select `anthropic` or `openai`, with sensible defaults and validation.
- Implement provider-agnostic prayer generation service that delegates to Anthropic or OpenAI drivers.
- Support provider-specific API keys/secrets stored in `.env` and surfaced in docs.
- Preserve existing prompts, safety filters, and UI flows with no regressions.
- Provide monitoring hooks (logging/metrics) for provider selection and failures.

## User Flow
1. Operator sets desired provider and keys in `.env` and restarts `./thywill start`.
2. Application boot validates configuration and instantiates the matching provider driver.
3. User requests an AI-generated prayer through existing UI/CLI.
4. Service sends prompt to chosen provider, handles errors/fallback, and returns normalized prayer text.
5. Prayer displays in feed/history exactly as before regardless of provider.

## Success Criteria
- Prayer generation succeeds with either provider when correct keys are present.
- Misconfiguration renders clear errors during startup and in CLI status checks.
- No template or API changes required for frontend clients.
- Logging shows provider choice and any fallbacks for observability.
- Documentation (`CLAUDE.md`, `AI_PROJECT_GUIDE.md`, `.env.example`) reflects new configuration options.
