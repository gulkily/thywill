# Offline Prayer Experience – Prayer Mark Duplication Bug

## Summary
Offline-queued prayer marks are being replayed multiple times after the browser reconnects, causing the mark count to jump by 3–5 instead of exactly one.

## Reproduction Steps
1. Load ThyWill in a supported browser.
2. Go offline (e.g., disable network in Chrome DevTools).
3. Click "Prayed" on a prayer and note the current count.
4. Reload the page one or more times while still offline.
5. Restore connectivity.
6. Reload the page and inspect the prayer count.

## Expected vs Actual
- **Expected**: The prayer count increases by exactly 1.
- **Actual**: The prayer count increases by several marks (3–5), indicating duplicate sync events.

## Initial Thoughts
- Repeated offline reloads may duplicate queue entries or reapply the offline badge updates, leading to multiple enqueued records.
- Service worker and foreground syncing both flush the IndexedDB queue; duplicates might exist because we add a new entry on each offline POST replay.
- Need to ensure idempotent queuing (single entry per prayer per offline action) or deduplicate during sync.
