# Bug 8 – Offline Feed Navigation Step 2 Remediation Plan

## Root Cause
Offline navigation triggers a full page request (`/feed?feed_type=...`). When the network is unavailable, the service worker falls back to a cached response for `/feed`, resetting the view to `all`. IndexedDB only stores the currently loaded feed snapshot, and the client UI lacks logic to hydrate alternative feeds without a server render. Consequently, offline users cannot switch feeds unless those exact pages were previously cached.

## Proposed Fix
- Update `service-worker.js` to prefer exact cache matches before falling back, so previously visited feed pages render offline.
- Extend `ThywillOffline` to expose `hasFeedSnapshot` for existence checks.
- Add data attributes to feed navigation elements for consistent offline styling control.
- Render all feed headings as hidden blocks and toggle them client-side via data attributes.
- Intercept feed navigation clicks when offline, hydrate the target feed from IndexedDB, update headings/nav state, and surface a fallback message if no snapshot exists.
- Maintain URL coherence (history state) when offline navigation occurs.

## Touchpoints
- `static/js/service-worker.js` – adjust navigation fallback logic.
- `static/js/offline-data.js` – expose snapshot existence helper.
- `templates/components/feed_navigation.html` – add metadata/data attributes.
- `templates/feed.html` – restructure headings and add offline navigation script.

## Testing Plan
- Manual: Visit multiple feeds online, go offline, switch feeds, ensure the correct view and heading render without hitting the network.
- Manual: Attempt offline navigation to a feed not yet cached; confirm graceful fallback message.
- Regression: Verify online navigation still performs full reloads and server-rendered headings look correct.

## Risks & Rollback
- Risk: Class rework for nav pills may introduce styling regressions. Mitigation: visual spot check in light/dark modes.
- Risk: Offline script could interfere with online navigation if mis-guarded. Mitigation: ensure `navigator.onLine` checks gate behaviour.
- Rollback: Revert modified JS/template files to previous revision and redeploy.
