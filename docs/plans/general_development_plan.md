# General Development Plan – Offline Prayer Experience Follow-up

## Immediate Priorities (0–2 days)
- **Bug #8 diagnosis** – Capture Step 1 plan for offline feed navigation so non-default feeds render from cache.
- **Manual regression** – Run full offline → online workflow in Chrome (all feeds, multiple marks) and capture findings.
- **Back-end dedupe validation** – Inspect recent prayer mark data to confirm timestamp-based dedupe behaves as expected.

## Near-Term Work (2–5 days)
- **Bug #8 remediation** – Implement client-side interception for feed navigation offline, ensure IndexedDB snapshots per feed, add tests/docs.
- **SQLite fixture fix** – Repair test setup so `pytest tests/test_public_prayer_service.py::test_is_prayer_public_eligible` passes, enabling automated coverage for offline behavior.
- **Telemetry review** – Analyze `thywill_offline_telemetry` entries to verify new success/failure signals and adjust logging thresholds.

## Medium-Term Enhancements (5–10 days)
- **Offline UI polish** – Surface queued mark counts in badge UI, ensure banners dismiss promptly after sync.
- **Documentation refresh** – Update `AI_PROJECT_GUIDE.md` and user-facing guides with offline tips (feed navigation offline, mark dedupe behavior).
- **Monitoring hooks** – Add optional server-side logging for deduped offline marks to spot patterns in production.

## Pending Decisions
- Determine whether to introduce IndexedDB schema versioning for per-feed snapshots (risk: larger cache footprint).
- Decide on automated browser tests (Playwright) to cover offline navigation and mark flows.

## Success Metrics
- All defined feeds render from cache within 2 seconds while offline.
- Offline marks sync once, reflected immediately offline, and confirmed via analytics (no duplicate DB entries).
- Pytest subset covering prayer marks runs clean (no missing-table errors).
