# Offline Prayer Experience – Step 3 Development Plan

1. Service worker & manifest foundation (≤2h)
   - Dependencies: none (start on feature branch).
   - Changes: add web app manifest, register service worker, set up precache list for shell assets, configure cache versioning utilities.
   - Testing: manual load to confirm service worker installs, `navigator.serviceWorker` registered, manifest passes `./validate_templates.py` if touched.
   - Risks: cache invalidation edge cases; mitigate with versioned cache keys and skipWaiting/clientsClaim gated behind feature flag.

2. IndexedDB bootstrapping for offline data (≤2h)
   - Dependencies: Stage 1.
   - Changes: create IndexedDB helper module, seed categories + recent prayers during online load, add fallbacks to read from IndexedDB when offline.
   - Testing: manual airplane-mode test to ensure categories render from cache.
   - Risks: schema migrations for IndexedDB; mitigate with versioned stores and defensive upgrade handlers.

3. Offline prayer mark queue & background sync (≤2h)
   - Dependencies: Stage 2.
   - Changes: log offline marks into IndexedDB queue with timestamps, update local UI state immediately for offline browsing, register Background Sync (with fallback polling), implement sync worker route for flush.
   - Testing: simulate offline mark creation, reconnect to observe queued writes hitting API, add unit tests for serialization/timestamp preservation.
   - Risks: Background Sync unsupported in some browsers; provide timed retry fallback to avoid data loss.

4. Connectivity status UI & telemetry (≤2h)
   - Dependencies: Stage 3.
   - Changes: add UI indicator component, hook into online/offline events and queue state (including queued mark counts), record telemetry for sync success/failure, document usage.
   - Testing: manual status toggle (chrome devtools offline), ensure banner updates and clears post-sync, add integration test if feasible.
   - Risks: notification fatigue; gate banner visibility to meaningful state changes and auto-dismiss on success.

5. Hardening & rollout checks (≤2h)
   - Dependencies: Stages 1-4.
   - Changes: feature flagging, update docs (`CLAUDE.md`, `AI_PROJECT_GUIDE.md`), add TodoWrite tracking, prep Step 4 summary template.
   - Testing: run full `./thywill test`, cross-check Lighthouse PWA audit, verify fallback behavior on unsupported browsers.
   - Risks: regression in existing session persistence; run regression smoke tests and adjust fallback order if conflicts appear.
