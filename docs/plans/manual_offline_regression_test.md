# Manual Test Script – Offline Prayer Experience Regression

## Goal
Verify end-to-end offline functionality: browsing feeds, recording prayer marks, and syncing back online without duplicates.

## Preconditions
- Run the latest build with `OFFLINE_PWA_ENABLED=true`.
- Clear application data (Cache, IndexedDB, LocalStorage) to start fresh.
- Use a Chromium-based browser (Chrome/Edge) with DevTools accessible.

## Steps

### A. Online Seeding
1. Open DevTools → Application → Service Workers and ensure the ThyWill service worker installs (Scope shows `/`).
2. Visit `/feed` and note the current feed counts.
3. Navigate to each target feed while online to seed snapshots:
   - Daily Priority
   - Prayers Needing Attention
   - New & Unprayed
   - Popular (Most Prayed)
   - My Prayers
   - Not Prayed Yet
   - My Prayer Requests
   - Recent Activity
   - Praise Reports
4. On one feed (e.g., Daily Priority), click a prayer’s “Prayed” button to ensure the offline cache captures the markup change.
5. Confirm no network or console errors appear.

### B. Offline Browsing & Marking
6. In DevTools → Network, set throttling to `Offline`.
7. Refresh `/feed`. Verify the All feed renders from cache within ~2 seconds.
8. Click each navigation pill offline:
   - Confirm headings and nav highlight update.
   - Verify prayers appear for feeds that were seeded online.
   - For any feed not previously opened online, ensure the fallback message (“Offline view not yet available…”) displays.
9. On at least two prayers, click “Prayed” while offline and watch that the badge increments and the offline indicator appears.
10. Reload the page while still offline to confirm queued marks and the current feed persist (no duplicate entries).

### C. Reconnection & Sync
11. Switch DevTools Network back to “Online”.
12. Watch for the offline banner to update and queued marks to clear (check console logs for flush events).
13. Reload `/feed` and verify the prayer counts increased by exactly one per offline mark.
14. Review IndexedDB (`Application → IndexedDB → thywill-offline → markQueue`) to ensure the queue is empty.
15. Refresh other feeds and confirm cached content matches server-rendered content.

### D. Logging & Cleanup
16. Inspect `localStorage['thywill_offline_telemetry']` for recent entries (queue success/failure) and note any anomalies.
17. Clear Application storage to prepare for the next test run.

## Expected Results
- Every seeded feed renders offline without network access.
- Offline prayer marks appear immediately and sync once after reconnection; no duplicate entries appear in lists or counts.
- Offline status banner and nav highlights behave consistently.
- IndexedDB mark queue is empty post-sync and telemetry shows success events.

## Notes
- If a feed doesn’t render offline, confirm the online seeding step (Step 3) included that feed.
- Use Browser DevTools’ “Application → Cache Storage” to confirm the service worker cached responses for each visited feed.
