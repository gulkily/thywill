# Repository Guidelines

## Project Structure & Module Organization
FastAPI entrypoints `app.py` and `thywill` delegate to `app_helpers/` (`services/`, `routes/`, `utils/`); AI provider drivers live in `app_helpers/services/ai_providers/`. Schemas stay in `models.py`/`migrations/`, UI assets in `templates/`+`static/`, tests in `tests/`, and planning docs in `docs/plans/`.

## Build, Test & Development Commands
- `python -m venv venv && source venv/bin/activate` then `pip install -r requirements.txt` to sync dependencies.
- `./thywill start` for the server; fall back to `uvicorn app:app --reload --port 8000` only when debugging internals.
- `./thywill test`, `pytest -m "unit"`, or `pytest --cov=app_helpers --cov=app` to exercise suites; tag slow cases explicitly.
- `./thywill migrate` after schema tweaks, `./thywill backup` before risky changes, and `./thywill status` to confirm database health.
- `./thywill config` to review paths, backup stats, and current AI provider/credential status.
- `python tools/update_env_defaults.py --dry-run` to check env drift, `./validate_templates.py` or `./check_templates.sh` ahead of template changes.

## Feature Development Workflow
Always follow the four-step plan in `FEATURE_DEVELOPMENT_PROCESS.md`. Create Step 1–3 documents in `docs/plans/` (`{feature}_stepN_*.md`), wait for approval between steps, and keep stages under two hours. Begin Step 4 only on a feature branch (e.g., `feature/membership-applications`) and implement stages sequentially, testing and committing after each.

## Coding Style & Naming Conventions
Use four-space indentation, type hints on new Python 3.8+ code, `snake_case` modules/functions, `PascalCase` models, and descriptive template filenames (`prayers_detail.html`). Prefer dependency injection over globals, keep services cohesive, and factor shared view fragments into `templates/includes/`.

## Testing, QA & Reviews
Pytest discovery is configured via `pyproject.toml` (`test_*.py`, `Test*`, `test_*`). Tag new cases with `@pytest.mark.unit|integration|functional|slow` and document skipped slow tests in PRs. Maintain deterministic fixtures, favour factories, and validate templates with the provided scripts. For schema changes run `./thywill validate-schema` when available and confirm archives with `./thywill heal-archives --dry-run` before modifying text archives.

## Commit, PR & Documentation Expectations
Write imperative, sentence-case commits (<65 chars) and expand details in the body. Link issues, call out migrations or backups, and add screenshots for template/UI work. After every change, refresh `CLAUDE.md` and `AI_PROJECT_GUIDE.md` with new commands, flags, or architecture notes. Avoid force pushes after review begins, and confirm tests plus backups before requesting merge.

## Security & Configuration Tips
Keep secrets in `.env`; regenerate via `.env.example` and env-defaults rather than manual edits. Track `AI_PROVIDER`, `ANTHROPIC_API_KEY`, and `OPENAI_API_KEY` per environment. Use `backup_database.sh` or `./thywill backup` before migrations or bulk imports, and keep AI keys confined to dev sandboxes.
