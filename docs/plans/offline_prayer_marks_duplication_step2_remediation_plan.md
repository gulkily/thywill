# Offline Prayer Marks Duplication – Step 2 Remediation Plan

## Root Cause Summary
When connectivity returns, both the foreground client (`prayer-sync.js`) and the service worker (`service-worker.js`) flush the IndexedDB queue concurrently. Each component issues its own POST to `/mark/{prayer_id}` before either removes the queued item, leading to duplicate prayer marks being persisted.

## Proposed Fix
- Single-source the queue flushing: if a service worker controls the page, delegate all network sends to it and have the foreground act as a thin UI layer.
- Add a `postMessage` channel so the service worker can return rendered HTML back to the active client after a successful sync (preserving live UI updates).
- Maintain the current foreground fetch logic only as a fallback when service workers are unavailable (legacy browsers or registration failure).
- Keep using Background Sync registration but ensure only the service worker performs the actual dequeuing when active.

## Touchpoints
- `static/js/prayer-sync.js` (flush orchestration, message listener, fallback path)
- `static/js/service-worker.js` (queue processing + client notifications)
- `static/js/offline-data.js` (no schema change expected, but may expose helper if needed)

## Testing Plan
- Manual: reproduce original repro steps ensuring mark count increments by exactly one.
- Manual: close the tab while offline, reopen after reconnect to confirm service worker Background Sync still posts once.
- Automated: smoke `pytest` target covering mark route (existing unit) to confirm no regression.

## Risks & Rollback
- Risk: UI may not refresh if message channel breaks; mitigate by verifying fallback path.
- Risk: Older browsers without service worker support must still flush; fallback path preserves current behavior.
- Rollback: Revert modified JS files and redeploy; no schema changes.
