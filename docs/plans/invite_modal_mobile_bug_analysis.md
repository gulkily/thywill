# Invite Modal Double-Render on Mobile Browsers – Debug Notes

## 🧪 Symptom
- On desktop Chrome the compact invite button opens a single modal via HTMX.
- On iOS Safari (and Firefox’s responsive/mobile simulator using an iPhone UA) two invite modals appear.
- Closing the top-most dialog reveals a duplicate underneath, confirming the markup was appended twice to `<body>`.

## 🐛 Root Cause Walkthrough (Rubber Ducking)
1. The button is wired for HTMX (`hx-post="/invites"`, `hx-target="body"`, `hx-swap="beforeend"`). HTMX should send the POST and append the returned fragment once.
2. We added `handleInviteClick` as a Safari-specific fallback after seeing HTMX stalls on WebKit. The handler fires for every click in order to detect Safari and manually `fetch('/invites')` when necessary.
3. Detection uses the user agent: any UA that contains `Safari` but not `Chrome`, `Firefox`, etc. is categorized as Safari. The Firefox mobile simulator uses the *exact same UA string* Safari reports (per Apple policy), so it slips through the filter.
4. Once the fallback runs it appends the HTML fragment. **But preventing the HTMX request is unreliable**: even with `event.preventDefault()`, `event.stopPropagation()`, and returning `false`, HTMX already queued its own listener and still fires the AJAX request. The request completes and HTMX also appends the modal. Result: two copies.
5. Real iOS Safari behaves the same—the UA check resolves to Safari, fallback appends once, HTMX also appends, giving identical “double modal” behaviour. When we spot it only in simulators it is because desktop Chrome doesn’t match the Safari UA, so the fallback never runs.

## 🔍 Why Firefox Still Duplicates After Guard Updates
- The simulator UA: `Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1` contains no forbidden substrings, so `isSafari` stays `true`.
- Even if we added more exclusions, every third-party iOS browser must use this Safari-style UA, so the check can’t safely distinguish “real Safari” from “Firefox on iOS”.
- Therefore the fallback still executes and we still rely on preventing HTMX, which does not consistently work because HTMX listens at a higher priority and sends its request before our inline handler returns.

## ✅ Path to a Proper Fix
1. **Pick a single transport**: choose either HTMX or a bespoke `fetch` and remove the dual wiring. The cleanest approach is to drop the `hx-*` attributes and let our JavaScript handle the POST for everyone. We can show a spinner and reuse the existing success/error handlers, eliminating the duplicate execution path.
2. **Or** keep HTMX and trigger the fallback only when HTMX raises an error. Hook into `htmx:sendError` / `htmx:responseError` and call the manual fetch there. No UA sniffing required.
3. If we must detect Safari, rely on positive feature detection (e.g., `CSS.supports('-webkit-touch-callout', 'none')` + `navigator.vendor === 'Apple Computer, Inc.'`) but still remove the HTMX attributes so there is only one code path when the fallback runs.

## 📌 Next Steps
- Decide between “HTMX only” vs. “Fetch only”. Given the maintenance cost, converging on one implementation (likely HTMX with error fallback) keeps behaviour consistent across browsers.
- After refactor, regression-test:
  - Desktop Chrome/Firefox (ensure single modal, proper focus trap)
  - Real iOS Safari 14+/17+ (confirm modal loads once)
  - Android Chrome (sanity)
- Once verified, remove the UA-sniffing helper and update `docs/plans/ios_safari_htmx_debugging.md` to record the new approach.
- ✅ Update: Adopted the fetch-only approach, removed HTMX attributes, and updated documentation to describe the unified flow.

---
Prepared while rubber-ducking the invite modal duplication issue reported on mobile browsers.
