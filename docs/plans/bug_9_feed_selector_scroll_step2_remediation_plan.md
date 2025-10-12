# Bug 9 – Feed Selector Scroll Reset Step 2 Remediation Plan

## Root Cause Summary
On page reload (online navigation), the horizontal feed selector (`#feedNavigation`) defaults to `scrollLeft = 0` because we never persist or restore the previous position. Although the active pill gains the correct state, the scroll container isn’t adjusted, so the pill can be hidden off-screen.

## Proposed Fix
- Record the selector’s `scrollLeft` in `sessionStorage` (key scoped to feed) prior to navigation.
- On DOMContentLoaded, read the stored value and apply it after the nav renders; fallback to `scrollIntoView` for the active pill if no stored value exists.
- Clear the stored value once applied to avoid stale positions across sessions.
- Ensure offline navigation script respects the same behaviour (reading/writing scroll state).

## Touchpoints
- `templates/components/feed_navigation.html` (add event listeners to store position; restore on load).
- `templates/feed.html` (optional helper to set initial scroll once offline script runs).

## Testing Plan
- Manual: While online, scroll to a far-right pill, click it, and confirm the selector remains positioned on reload.
- Manual: Repeat for multiple feeds; ensure behaviour persists across tabs/windows.
- Manual offline regression: Switch feeds offline and confirm the existing offline script still honours scroll state.

## Risks & Rollback
- Risk: Stored scroll positions may misalign on viewport size changes; mitigate by bounding to max scroll width.
- Risk: JS execution order may clash with existing indicator updates; ensure restoration runs before indicator checks.
- Rollback: Revert navigation script changes; no server or schema impacts.
