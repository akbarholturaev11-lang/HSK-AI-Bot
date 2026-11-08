# HSK AI PWA — iPhone Home Screen tutorial video asset

The Li onboarding UI offers an iPhone Safari installation tutorial **after a
verified PWA account returns from provider registration and the onboarding
profile has been saved successfully**. The install guide never grants account
access, Pro, push permission or a paid subscription.

## User-supplied video prepared (2026-11-09)

The uploaded recording was inspected and transcoded with ffmpeg, preserving
the 512×1114 portrait framing, 30 fps and 16.345-second duration.

| | Uploaded source | Optimized Safari asset |
|---|---|---|
| Size | 6,624,465 bytes | **709,956 bytes** |
| Codec | H.264 + AAC | H.264 (yuv420p) + AAC |
| Bitrate | 3.24 Mb/s | **0.347 Mb/s** |
| Progressive MP4 | not relied upon | **moov** offset 36, before **mdat** 18940 |
| Verification | – | SSIM vs original: **0.993621** |

Optimized file SHA-256:
`727be15b30229aedffee780eab61ee781ef3727e9cd7bcf8af5aab6d99bacb8f`

Reproducible command:

```bash
ffmpeg -i YOUR_ORIGINAL.mp4 \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset slow -crf 27 -profile:v main -level:v 3.1 \
  -pix_fmt yuv420p -c:a aac -b:a 32k -ac 1 \
  -movflags +faststart app/static/assets/onboarding/iphone-home-screen.mp4
```

**Transport note:** This compressed MP4 exists as a chat artifact, **not yet as
a GitHub repository blob**. The connected GitHub text-file interface cannot
read the local binary artifact. Use the actual optimized MP4 delivered in this
conversation and add its exact bytes to the feature branch at the fixed path
above (do not mistakenly add the 6.6 MB original). Confirm SHA-256 in the
checkout. Until then, the route correctly returns 404 and the UI displays a
three-step RU/UZ/TJ guide.

**Content review:** The recording appears to show a truncated older
`telegram-chinese-bot-...` address on the iPhone's Add to Home Screen screen.
Before publishing, confirm that this refers to the intended currently supported
PWA hostname; otherwise re-record the step with the official URL.

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
