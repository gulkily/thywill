# Offline Prayer Marks Duplication – Step 3 Resolution Summary

## Fix Overview
- Delegated offline prayer mark syncing exclusively to the service worker when it controls the page, preventing parallel foreground fetches.
- Added queue-processing guardrails and a broadcast channel so the service worker can stream rendered mark updates back to open clients.
- Added backend dedupe for offline marks (username + timestamp) so repeated sync attempts no longer create duplicate records or archive entries.
- Retained the existing foreground flush path as a fallback for browsers without service worker support, including telemetry clarity.

## Tests Run
- `pytest tests/test_public_prayer_service.py::test_is_prayer_public_eligible -q` *(fails: existing fixture lacks `user` table; unrelated to this bugfix)*
- Manual browser verification pending (requires offline/online toggle UI)

## Follow-ups
- Perform a manual offline/online regression in Chrome/Edge to confirm counts stay accurate and UI updates arrive via service worker messages.
- Investigate and fix the longstanding SQLite fixture setup so targeted pytest checks can execute without schema errors.
