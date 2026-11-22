# Launch mark, Pro panda and the Pro/Trial palette

Owner request (2026-11-22): a unique minimalist opening effect, a Pro panda
with its own effects delivered as easy-to-place components, and one colour
set for Pro and Trial windows. Owner choices: build both components; Pro and
Trial use the **light paper + gold accent** look.

## What is shipped in this change

| Piece | PWA | Android | Wired? |
| --- | --- | --- | --- |
| Pro/Trial colour set | `app/static/assets/brand/hsk-pro-theme.css` (`--hsk-pro-*`) | `core/design/ProColors.kt` | Trial window uses it (below) |
| "Knot Thread" launch mark | `app/static/assets/brand/hsk-launch-mark.{js,css}` | `core/design/components/HskLaunchMark.kt` | **No** |
| Pro panda + halo + spark burst | `app/static/assets/characters/hsk-pro-panda.{js,css}` | `feature/limit/ProPanda.kt` | **No** |
| One-time gold glint for cards/badges | `HSKProPanda.glint(el)` (same files) | `Modifier.hskProGlint()` in `core/design/components/HskProGlint.kt` | **No** |

The Trial window recolour **is** live: `course_v3_li_onboarding.html` (Pro intro
and trial steps), the installed-PWA trial layer in `course-v3.html`
(`.pwa-checkout-trial` background + theme-color, PWA-browser only) and the
status-bar edge in `iphone-pwa-inline-pro-bridge.js` moved from ink `#211D17`
to the paper/gold palette. Android Trial (`LiOnboardingChoices`) and the Pro
limit sheet were already on the light paper surface, so no Android screen was
recoloured. Not changed: `course-v3.html` `.levelup.sales-bridge` (shared with
the Telegram Mini App), copy, prices, buttons' actions, trial grant, access.

Contract test: `tests/test_launch_mark_pro_panda_contract.py` (timeline parity,
canonical panda drawing, palette tokens, "not wired" boundary). Android unit
tests: `HskLaunchMarkTest`, `ProPandaTest`.

## Design rules kept

- **No new character.** The Pro panda is the canonical course panda: the PWA
  drawing is the inline Pro sheet `pandaSvg` path for path, only class prefix and gradient id differ (guarded by the
  contract test); Android wraps `CoursePandaMascot`. The offer-only `gift`
  pose is not exposed.
- Effects play **once** and settle (celebrate bounce ×3, burst 0.8 s, glint 1 s).
- `prefers-reduced-motion` / Android "remove animations": static halo, no
  burst/glint, launch mark shows its finished frame and finishes at once.
- No text was added (wordmark "HSK AI" is the brand), so no RU/TJ/UZ keys.
- No libraries, no images: inline SVG/CSS and Compose Canvas only.

## How to place them

### PWA

```html
<link rel="stylesheet" href="/assets/brand/hsk-pro-theme.css?v=<date>-<blob12>">
<link rel="stylesheet" href="/assets/characters/hsk-pro-panda.css?v=…">
<script src="/assets/characters/hsk-pro-panda.js?v=…"></script>
<div class="my-panda-slot" style="width:120px;height:120px"></div>
<script>
  HSKProPanda.mount(slot, {pose: "pro"});          // limit / upsell
  HSKProPanda.mount(slot, {pose: "celebrate", burst: true}); // Pro just activated (server-verified)
  HSKProPanda.glint(document.querySelector(".pro-card")); // once, on appear
</script>
```

Launch mark (replacing the Golden Logo is a separate decision, see risks):

```html
<link rel="stylesheet" href="/assets/brand/hsk-launch-mark.css?v=…">
<script src="/assets/brand/hsk-launch-mark.js?v=…"></script>
<div id="launch"></div>
<script>HSKLaunchMark.mount(document.getElementById("launch"), {onDone: hideSplash});</script>
```

PWA asset references must be content-addressed (`?v=<date>-<git blob sha1[:12]>`,
`tests/test_iphone_pwa_asset_versions.py`). In the inline Pro sheet the panda
already exists; to switch it to the shared module, replace `pandaSvg()` in
`iphone-pwa-inline-pro.js` with `HSKProPanda.render(pose)` and add the CSS to
`_PWA_INLINE_PRO_HTML` in `app/api/pwa_auth.py`.

### Android

```kotlin
ProPanda(Modifier.size(120.dp))                         // Pro / limit sheet
ProPanda(Modifier.size(120.dp), celebrate = true)       // Pro activated: bounce + burst
Surface(Modifier.hskProGlint(key = offerId)) { … }      // Pro card, glint once per key
HskLaunchMark(onFinished = { /* leave splash */ })
```

Use `ProColors.*` instead of hard-coded hex values when touching a Pro/Trial
screen (`SectionLimitOverlay.kt` still has literal colours close to the palette).

## Risks before swapping the shipped launch

- The Golden Logo (`#hsk-launch-splash`, `HskBrandLoader`) is synchronised with
  `hsk-launch-gold.mp3` and two haptics at 570/1910 ms and locked by
  `tests/test_launch_feedback_contract.py`. A swap must re-time or drop the
  sound/haptics on both platforms and update that test in the same change.
- `course-v3.html` is shared with the Telegram Mini App; scope a swap to
  `html.hsk-pwa-browser` and Android unless the Mini App is explicitly in scope.
- The splash must never delay the first usable shell
  (`docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`).

Analytics Impact: not applicable (visual-only; no new behaviour or event).
Monitoring Impact: not applicable (no new route, flow or failure path).
