# Nicene Creed Display – Step 3: Development Plan

1. Create Nicene Creed page template and route
   - Dependencies: Step 2 approval; confirm final creed text source
   - Changes: Add `templates/nicene_creed.html` with semantic headings and responsive text; register a new route (likely in `app_helpers/routes/public.py` or equivalent) mapped to `/nicene-creed`; ensure route allows unauthenticated access but renders identically for authenticated users
   - Testing: Render page locally via `./thywill start` (or `uvicorn app:app --reload --port 8000`) and check light/dark themes; run `./validate_templates.py`
   - Risks: Misplaced route registration causing auth redirect; inconsistent text formatting

2. Surface navigation links for both audiences
   - Dependencies: Stage 1 complete
   - Changes: Add link from the public homepage hero/CTA region; update authenticated navigation (e.g., `templates/menu.html` or relevant component) with a “Nicene Creed” entry pointing to `/nicene-creed`; ensure ARIA/keyboard interactions remain intact
   - Testing: Manual click-through while logged out and logged in; responsive nav check; re-run `./validate_templates.py`
   - Risks: Navigation layout overflow on smaller screens; duplicate links confusing users

3. Regression checks and documentation updates
   - Dependencies: Stages 1–2 complete
   - Changes: Run targeted tests (`./thywill test` or `pytest -m "unit"` if feasible); update `AI_PROJECT_GUIDE.md` / `CLAUDE.md` if new navigation patterns warrant mention; prepare Step 4 implementation summary
   - Testing: Automated tests + manual smoke of public homepage and authenticated dashboard; confirm new links respect existing auth logic
   - Risks: Existing flaky tests delaying completion; missing documentation expectations
