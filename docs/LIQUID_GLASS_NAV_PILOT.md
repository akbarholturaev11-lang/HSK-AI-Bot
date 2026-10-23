# Mini App Liquid Glass bottom navigation — opt-in pilot

## Scope
- Based on `dashersw/liquid-glass-js` (MIT) WebGL shader, plus local `html2canvas@1.4.1` (MIT).
- Uses the existing five `#nav button[data-s]` buttons; **does not replace** `App.show`, Telegram SDK, learning or account/access code.
- Existing gradient/backdrop nav is the unchanged default for everyone.
- Testing opt-in: `/course-v3?liquid_glass=1` (or `/course-v3.html?liquid_glass=1`) on **a preview/staging deployment of this branch only**.
- Remove the query to restore the previous navigation. No user preferences or feature flags are persisted.

## Assets and licensing
- All JS/CSS comes from `/assets/liquid-glass/{filename}` (same-origin allowlist in `app/main.py`).
- No runtime CDN or GitHub requests from the Liquid Glass code.
- `container.js`: fork of upstream MIT `container.js`; changes marked at file header. `LICENSE` included.
- `html2canvas.min.js`: html2canvas 1.4.1 minified bundle mirrored from the Apache magpie-site GitHub repository; upstream project is `niklasvh/html2canvas`. `html2canvas.LICENSE` included.
- Integration review compared the vendored bytes with `package/dist/html2canvas.min.js` from the official npm 1.4.1 tarball: exact match, SHA-256 `e87e550794322e574a1fda0c1549a3c70dae5a93d9113417a429016838eab8cb`.
- The upstream `button.js` is intentionally **not** imported. The production nav buttons keep their own accessibility, routing and event handlers; the glass renderer is visual-only.

## Rendering and fallback
- The WebGL shader refracts and blurs a client-side DOM snapshot. This is **not Apple's proprietary native Liquid Glass renderer**.
- Snapshot excludes the nav and startup splash; does not read cross-origin images without CORS.
- After real WebGL initialization, a glass canvas is shown behind the original buttons. Refresh is debounced after tab changes, scroll and viewport resizing, with >=1.1s minimum capture gap.
- If scripts, capture, WebGL or shader fail, the existing CSS glass navigation stays available. Reduced-transparency users keep the solid accessible style.
- Known caveat: DOM rasterization costs CPU/GPU; the initial capture can be delayed on iOS Telegram. Background scrolling/animated content may appear stale between refreshes; physical-device QA required.

## QA procedure (not a claim of a completed device test)
1. Deploy **this branch to a separate preview/staging environment**, not production; open `/course-v3?liquid_glass=1`.
2. Compare the same preview route **without** the query; original nav remains.
3. On Telegram iPhone/Android: test five sections, active pill, speech center FAB, modal/back navigation and HSK 3.0 practice gating.
4. Test course scroll under nav, fast section changes, dark/light and 320px screens, top and bottom safe areas.
5. Check DevTools network for JS/CSS 200 same-origin, no requests to `jsdelivr`/`GitHub`; check console errors and iOS memory/frame drops.
6. Disable WebGL or emulate reduced transparency: nav remains usable.
7. After QA, decide whether to promote or discard. **Do not merge into main or deploy production based only on syntax/contract checks.**

## Files
- `app/static/course-v3.html` opt-in loader
- `app/static/assets/liquid-glass/*` renderer, styles, license and snapshot dependency
- `app/main.py` allowlisted static route
- `tests/test_liquid_glass_nav_pilot.py` static contract smoke tests
- `tests/test_telegram_sdk_asset.py` actual HTTP byte delivery and unknown/traversal-file denials
- `tests/e2e/test_miniapp_smoke.py` opt-in/default isolation, delayed/failed CSS, reduced transparency, WebGL failure, actual shader/capture and context loss in UZ/RU/TJ at 320/390px

## Integration checkpoint — 2026-10-23

The owner authorized merging pilot source `277c22c53e76bffc162ec14f2c8855c499c79134`
into `codex/p3-main-integration-20261020` and loading it into the local test Bot.
The HTML merge retains the integration branch's current localized helper cache
tokens. No lesson, answer, grade, auth, payment, subscription or progress source
was changed by the pilot. Default navigation still does not request pilot assets.
Backend CI now explicitly runs the pilot tests, including the existing three
pytest functions which were not covered by its earlier unittest commands.

Local checks passed: 460 P0 tests, 19 existing navigation/UI checks, 12 pilot/static
checks, 25 critical learning/checkout checks, five real HTTP asset tests and all
P0 read-only checks (53 generated artifacts, zero stale). Software WebGL and
synthetic browser APIs do not establish physical iPhone/Android acceptance.
See `localization/RESUME_NEXT_CHAT.md` for active test-server state and CI evidence.
