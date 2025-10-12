# Offline Feed Navigation – Step 1 Diagnosis Plan

## Problem Statement
While offline, selecting a non-default feed (e.g., `feed_type=daily_prayer`) reloads the page but falls back to the `all` feed, preventing offline browsing of other views.

## Known Context
- Feed navigation uses standard anchor tags that request `/feed?feed_type=...`.
- Service worker handles navigation requests via `handleNavigationRequest`; on fetch failure it falls back to cached `/`.
- IndexedDB currently stores snapshots for the active feed only (no per-feed caching).
- Offline data helper `ThywillOffline.ensureFeedReady` hydrates the current feed from cache but isn’t aware of feed switching.

## Hypotheses
1. **Cache fallback to `/`**: Navigation requests for `/feed?feed_type=...` miss the cache and return the cached default, resetting to `all`.
   - *Validation*: Inspect service worker cache entries and console logs while offline; confirm fallback path is hit.
2. **Missing per-feed snapshots**: IndexedDB stores only the current feed; switching feeds offline yields no data so UI defaults to `all`.
   - *Validation*: Check `feedType` keys in IndexedDB after browsing multiple feeds online.
3. **Client-side hydration logic**: `ThywillOffline.ensureFeedReady` uses `data-feed-type` but may run before the new feed type is set during offline navigation.
   - *Validation*: Simulate navigation via HTMX-like swap or manual DOM updates and trace the JS execution order.

## Impacted Areas
- `static/js/service-worker.js` (navigation handler, cache lookup)
- `static/js/offline-data.js` (feed snapshot management)
- `templates/components/feed_navigation.html` (could benefit from intercepting clicks offline)
- `templates/feed.html` (DOM hooks for offline hydration)

## Diagnosis Success Criteria
- Reproduce the issue consistently in a controlled environment.
- Confirm which hypothesis (or combination) causes the fallback.
- Decide whether the fix should involve service worker routing, client-side interception, or expanded IndexedDB storage.
