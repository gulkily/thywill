# Offline Prayer Marks Duplication – Step 1 Diagnosis Plan

## Problem Statement
Prayer marks queued while offline are syncing multiple times after reconnection, inflating mark counts by 3–5 instead of exactly one.

## Known Context
- Offline queue stored in IndexedDB via `window.ThywillOffline` helpers.
- `prayer-sync.js` intercepts HTMX POSTs when offline and enqueues an entry with timestamp metadata.
- Sync execution happens in both foreground (via `flushQueue`) and service worker background sync (`service-worker.js`).
- Queue entries are removed only after a successful POST response.

## Hypotheses
1. **Concurrent Flushes**: Foreground and service worker flush routines run simultaneously when connectivity returns, each replaying the same queued item before it is deleted.
   - *Validation*: Instrument logs around `flushQueuedMarks` invocations in both contexts; observe duplicate fetches in dev tools.
2. **Duplicate Queue Entries on Reload**: Offline reload triggers `enqueuePrayerMark` again for existing actions due to DOM rehydration or repeated HTMX events.
   - *Validation*: Inspect queue contents with DevTools (IndexedDB) after offline reloads without re-clicking the button; check for multiple items.
3. **Server-Side Duplicate Handling**: Backend route may be called multiple times because service worker retries on non-200 responses, causing additional marks.
   - *Validation*: Capture network logs to confirm status codes; ensure duplicates occur even with 200 responses.

## Impacted Areas
- `static/js/prayer-sync.js`
- `static/js/service-worker.js`
- `static/js/offline-data.js`
- API endpoint `/mark/{prayer_id}` (FastAPI route)

## Diagnosis Success Criteria
- Reproduce the duplication consistently in local environment.
- Identify precise trigger (e.g., concurrent flush vs duplicate queue entries).
- Decide on remediation strategy (single-source flush, dedupe guard, or backend idempotency token).
