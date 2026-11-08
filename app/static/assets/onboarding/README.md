# HSK AI PWA — iPhone Home Screen tutorial video asset

The Li onboarding UI offers an iPhone Safari installation tutorial **after a
verified PWA account returns from provider registration and the onboarding
profile has been saved successfully**. The install guide never grants account
access, Pro, push permission or a paid subscription.

## Approved video location

- File: `app/static/assets/onboarding/iphone-home-screen.mp4`
- Public, immutable path: `GET /assets/onboarding/iphone-home-screen.mp4`
- Format: H.264/AAC or silent H.264, MP4 with fast-start metadata
  (`-movflags +faststart`), portrait, up to 1080x1920, 15–45 seconds,
  reasonably compressed (target under 10 MiB).
- No other path is dynamically fetched from query strings or user input.
- When this MP4 **does not exist** (currently absent), the route intentionally
  returns HTTP 404. The UI hides the broken player, shows the exact canonical
  RU/UZ/TJ three-step text guide, and offers a Continue action.

Record an actual iPhone **Safari** demonstration using a neutral test device
with notifications/account emails/secrets hidden:

1. Open the official PWA URL in Safari.
2. Tap the Safari Share control, scroll to **Add to Home Screen**.
3. Tap **Add**, then demonstrate launching HSK AI from its new icon.

Upload ONLY the reviewed recording with the exact fixed filename. A reviewed
video must not claim the app can install itself, bypass iOS prompts or enable
Web Push without separate permission. The HTML uses `<video controls
playsinline preload="metadata">`, not forced autoplay. Browser `Range` video
requests are handled by Starlette `FileResponse` when the file exists.

## QA after the MP4 is published

- New account using iPhone Safari: dialog opens once after confirmed onboarding
  save; video loads and plays with controls.
- On media fetch failure: no broken video or spinner; three textual steps stay
  accessible. The learner can continue.
- Existing, already-onboarded users, Telegram Mini App, desktop/Android,
  installed iPhone standalone PWA: no first-time prompt.
- Dismissed guide: local per-account flag prevents repeated display in the same
  browser; account changes use a distinct key.
- Verify Safari real device, offline fallback, landscape/safe-area, reduced
  motion, VoiceOver labels, and that the guide never asks for push permission.

**This README is asset documentation, not a published video.** Do not mark the
video itself finished before the MP4 is actually created, added and browser
tested.
