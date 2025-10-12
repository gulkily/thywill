# Bug 9 – Feed Selector Scroll Reset Step 1 Diagnosis Plan

## Problem Statement
After selecting a feed that requires horizontal scrolling, the page reloads (online mode) and the selector snaps back to the start, hiding the active pill.

## Known Context
- Feed navigation uses standard anchor tags; online navigation triggers full reloads.
- The nav container is horizontally scrollable (`#feedNavigation`).
- No script currently preserves `scrollLeft` across reloads.
- Offline mode now intercepts clicks and manages scroll/active state client-side, so the issue occurs primarily online.

## Hypotheses
1. **Scroll position not persisted** – On reload, DOM defaults to `scrollLeft=0` since we never restore it.
   - *Validation*: Log scroll position before navigation and verify it resets on DOMContentLoaded.
2. **Server render doesn’t focus active pill** – The page reload doesn’t scroll into view even though the active class is applied.
   - *Validation*: After reload, check `document.querySelector('[aria-current="page"]')` – confirm active pill is off-screen.
3. **Race with JS initialization** – Existing navigation script (scroll indicators) may run after reload and override manual scroll adjustments.
   - *Validation*: Add temporary script to set `scrollLeft` on DOMContentLoaded and observe if subsequent logic overrides it.

## Impacted Areas
- `templates/components/feed_navigation.html` (selector markup & JS)
- Possible update to `templates/feed.html` for inline script to restore scroll.
- Optional use of `sessionStorage` to persist scroll position.

## Diagnosis Success Criteria
- Reproduce the reset reliably, capturing before/after `scrollLeft` values.
- Confirm the absence of scroll restoration logic is the core cause.
- Decide on persistence strategy (encapsulate in nav script vs. shared helper).
