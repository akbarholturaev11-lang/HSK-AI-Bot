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
- `html2canvas.min.js`: stock html2canvas 1.4.1 minified bundle, SHA-256 provenance reported by Apache magpie-site: `e87e550794322e574a1fda0c1549a3c70dae5a93d9113417a429016838eab8cb`. `html2canvas.LICENSE` included.
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
