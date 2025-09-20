# OpenAI Backend Support - Step 3 Development Plan

1. **Configuration & Validation Scaffold** (≤2h)
   - Dependencies: Step 2 approved.
   - Changes: Extend `.env.example`, config loading, and CLI status to accept `AI_PROVIDER` plus OpenAI keys; add startup validation helper.
   - Testing: `pytest tests/test_env_creation.py::TestEnvCreation::test_missing_ai_keys` (add new coverage); manual `./thywill status` check.
   - Risks: Mis-reading existing Anthropic defaults—mitigate by keeping backwards-compatible fallbacks.

2. **Provider-Agnostic Service Refactor** (≤2h)
   - Dependencies: Stage 1 configuration helper.
   - Changes: Introduce `app_helpers/services/ai_providers/` with base interface, move Anthropic logic into driver, update `generate_prayer` path to use factory.
   - Testing: `pytest tests/test_integration.py::TestPrayerGeneration` (update/extend); run lint/static checks if available.
   - Risks: Breaking prayer generation flow—mitigate with integration test adjustments.

3. **OpenAI Driver Implementation** (≤2h)
   - Dependencies: Stage 2 interface ready.
   - Changes: Implement OpenAI driver using `openai` SDK, map responses to shared schema, handle errors/fallback to Anthropic if configured.
   - Testing: Add unit tests for driver (mock SDK); manual smoke run via `./thywill start` + UI prayer generation with OpenAI key.
   - Risks: API differences or rate limits—mitigate with defensive error handling and timeouts.

4. **Documentation & Observability Updates** (≤2h)
   - Dependencies: Previous stages merged.
   - Changes: Update `CLAUDE.md`, `AI_PROJECT_GUIDE.md`, `AGENTS.md`, `.env.example`; add logging/metrics for provider selection and failures.
   - Testing: `pytest --maxfail=1` regression run; manual log inspection during prayer generation.
   - Risks: Missing doc sync—mitigate via checklist review before completion.
