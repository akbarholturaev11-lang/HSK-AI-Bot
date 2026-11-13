# HSK AI Voice Orb — isolated visual tuning handoff

**Branch:** `feat/voice-orb-motion-lab-20261113` (keep work isolated; do NOT merge or push to `main` until explicit owner approval of the visual result)

## Goal

Have ONE dedicated coding agent iteratively tune the existing **HSK AI Red Orb** visual look, exact three sizes and responsive animation for **listening / thinking / speaking**, without introducing app/runtime integration yet.

## Current editable prototype

- `app/static/voice-orb-motion-lab.html` — standalone no-network Canvas 2D visual lab, controls for idle/listening/thinking/speaking/connecting/error, synthetic audio amplitude, all 3 exact sizes visible simultaneously.
- Visual starting point: `app/static/iphone-pwa-voice.html` Red Orb Canvas renderer (`render(ms)`, current `#orb` CSS).
- Native reference only: `android/app/src/main/java/com/pomp/hskai/feature/voice/VoiceV8Orb.kt` and `VoiceV8Screen.kt`.
- Product design context: UIUX-011 in the separate consolidated HSK AI UI/UX planning document, if available.
- Optional upstream motion inspiration: `Jakubantalik/thinking-orbs`. This is an inspiration for restrained dot/pattern motion, **not** permission to replace the original HSK AI orb or import React Native / Skia.

## Immutable size presets

| Context | Visible orb size |
| --- | --- |
| Focus | **173 × 173 CSS px** on PWA; **173 × 173 dp** on Android |
| Chat | **80 × 80 CSS px** on PWA; **80 × 80 dp** on Android |
| Typing | **62 × 62 CSS px** on PWA; **62 × 62 dp** on Android |

Keep the three sizes crisp and proportional; adjust particle count, dot radius, alpha and speed per size. Never stretch a 64px preset unmodified.

## Visual behavior to tune in the lab

- **Idle:** original red pearl orb and subtle slow breathing; no busy dot decoration.
- **Listening:** visible but restrained reactive dot-wave/ripple; amplitude in the lab is synthetic. Do not claim live microphone integration.
- **Thinking:** graceful coherent orbital/particle organization distinct from listening. Motion should feel deliberate rather than random and distracting.
- **Speaking:** fluid light and dot pulse reacting to synthetic amplitude, with a noticeable distinction from listening. Actual TTS/playback audio-meter wiring is a future integration phase.
- **Connecting:** subtle, distinguishable slow progress cue. **Error:** quiet, readable, non-alarming failure appearance, without hiding the error copy.
- Preserve red/pearl brand colors, shape, glaze, highlights and consistency across all states. Avoid swapping in a new orb unrelated to the source visual.

## Strict non-goals for this branch

- Do NOT touch production PWA or Android Voice screens, state machine, live session/audio pipeline, TTS, permissions, quota, sockets, authentication, payments, navigation or backend.
- Do NOT introduce React/React Native, new build dependencies or services just to animate this orb.
- Do NOT update the global UI/UX skill or broad project plan automatically from exploratory visual experiments.
- Do NOT commit directly to `main`, open a merge-ready PR or claim production integration.
- Do NOT simulate payments or disclose real account/voice data in the visual lab.

## Single-agent workflow

1. Read `AGENTS.md`, scoped skill `.agents/skills/hsk-ai-ui/SKILL.md`, and the current prototype/source.
2. Edit **only** `app/static/voice-orb-motion-lab.html` and, if essential, this handoff file on the **existing branch**. No new branch and no unrelated changes.
3. Iterate on the three state patterns using screenshots/video and compare the focus/chat/typing geometry. Prefer compositional tuning (alpha, size, speed, contrast, particle distribution) over new dependencies.
4. Keep the effects visually distinguishable, non-childish and readable over the real brand background. Record brief before/after screenshots and the setting changed.
5. Validate normal and reduced motion; 320/390/430px mobile widths, Chromium and WebKit where available, state switching, resizing, hidden-tab behavior and no JavaScript errors.
6. Present the **prototype preview and commit SHA** to the owner for approval. Only after separate approval should another task port the accepted settings to production PWA and Android.

## Acceptance criteria

- Precisely 173 / 80 / 62 visible CSS px in the HTML lab, at normal and 2× DPR.
- One recognizable HSK AI red/pearl orb for every state and size.
- Listening, thinking and speaking show intentionally different animation signatures.
- No dependency on a live backend, microphone, TTS or React Native.
- Rendering capped at a sensible rate (the lab currently targets ~30 fps), paused when hidden; reduced-motion displays a stable composition.
- The learner production files and `main` remain unchanged.

## Implemented visual pass — 2026-11-13 (prototype only)

**Selected pattern:** restrained, size-aware Canvas overlays over the original
red/pearl base. Comparison with the starting lab's shared, relatively dense
particle formula favored separate visual signatures and fewer dots at 62/80 px:
- **Listening:** a soft amplitude-responsive crescent/ripple with 5/7/11 dots
  at Typing/Chat/Focus and a restrained inner contour.
- **Thinking:** two coherent, slowly counter-rotating elliptical tracks (one
  simplified track at 62px), 5/7/11 small pearl points. No random per-frame jitter.
- **Speaking:** central harmonic wave lines (2/3/4 bands) with 3/5/9
  amplitude-driven points and gentle pearl light bloom; visually distinct
  from the listening arc.
- Idle/connecting/error stay quiet; a readable local state label sits outside
  the orb. The original red/pearl gradient, waves, glaze and shape remain.
- State transitions crossfade weighted overlays over 410ms; rapid repeated
  selections continue from the current blend instead of resetting or popping.
  Audio amplitude has a ~105ms smoothing constant. All presets retain the
  fixed **173/80/62 CSS px** dimensions.
- A local All/Focus/Chat/Typing view picker makes individual size inspection
  possible. Default shows all three. The slider is synthetic only; no actual
  sound, microphone, network, API, backend or TTS integration.
- RAF capped at 30 fps, no RAF when reduced motion is requested, pause on hidden
  tab, repaint on resize/DPR change; internal canvas pixel size matches CSS×DPR
  up to a 3× cap. No new dependency or runtime framework.

### Local verification evidence

- node --check on extracted inline JS: **pass**.
- Chromium headless: viewport widths **320, 390, 430px**, DPR **2×**;
  six states, three exact CSS sizes, all size-picker modes, amplitude input,
  no horizontal overflow and no page/console JavaScript errors: **pass**.
- Chromium reduced motion: **320px / 3× DPR**; stable single-frame
  composition, selected state and slider still update, FPS remains zero: **pass**.
- Repeated state changes (42 switches), manual visibility hidden/resume,
  live reduced-motion toggle and resume: **pass**.
- Headless Chromium sampled **22–23 displayed FPS** while the renderer is
  capped at 30; performance differs from a real iPhone/Android device.
  Chromium JS heap after explicit GC sampled ~1008 / 997 / 997 KiB across
  three intervals (short-run smoke check, not a long-duration leak proof).
- Visual review: compared Idle/Listening/Thinking/Speaking/Connecting/Error
  Focus captures and the 390px full-page composition; patterns have separate
  visual signatures without making the small orbs crowded.
- **WebKit/iOS browser not available** in the execution environment; needs
  an actual WebKit/iPhone validation before any production port.
- Screenshots were inspection artifacts outside the tracked repo: keep this
  branch restricted to the prototype HTML and this handoff file only.

**Analytics Impact:** none; standalone local synthetic renderer with no
product user flow or telemetry events.

**Release boundary:** DO NOT merge to main or copy into production
PWA/Android Voice without the owner's separate visual approval and real-device
checks. No production source was changed by this task.
