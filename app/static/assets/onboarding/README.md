# HSK AI PWA — iPhone Home Screen tutorial asset

## Approved current recording (replaced 2026-11-09)

The owner supplied a replacement recording of the official `hskai.app/iphone-pwa`
Home Screen flow. This supersedes the earlier video which showed an obsolete
`telegram-chinese-bot-...` / Railway address. Visual frames of the new source
show `https://hskai.app/iphone-pwa/...` in the iOS Add to Home Screen sheet.
Actual iPhone Safari playback and final production deployment must still be checked.

| Property | Supplied recording | Committed Safari file |
|---|---:|---:|
| Duration | 13.267 s | 13.267 s |
| Resolution | 512×910 (portrait, 30 fps) | 512×910 |
| Codec | H.264 High + AAC | H.264 Main (yuv420p) + AAC |
| File size | 4,066,499 bytes | **574,244 bytes** |
| Delivery | MP4 | MP4 with fast-start `moov` before `mdat` |

Source SHA-256:
`2921aac471d37b9a4a247b7aec8d1a7d60e35755ccbbfa69b467441e9374b410`

Approved GitHub-file SHA-256:
`3e099a0c0489d9f0dc3e358490f5d87f2682462204eac7668b557c918874d15e`

The source was integrity-verified before transcode. GitHub Actions one-time
import `42649461883` successfully committed the optimized MP4 to
`app/static/assets/onboarding/iphone-home-screen.mp4`. Different FFmpeg
versions produce different byte hashes despite equivalent encoding settings;
the source hash is fixed and tests pin the exact committed output hash.

For reproduction use FFmpeg:
```sh
ffmpeg -i YOUR_ORIGINAL.mp4 \
  -map 0:v:0 -map '0:a:0?' \
  -c:v libx264 -preset slow -crf 26 -profile:v main -level:v 3.1 \
  -pix_fmt yuv420p -c:a aac -b:a 32k -ac 1 \
  -movflags +faststart app/static/assets/onboarding/iphone-home-screen.mp4
```

## Serving and UX contract

- Canonical GET path: `/assets/onboarding/iphone-home-screen.mp4`; the
  fixed FastAPI route supports HTTP Range requests and skips gzip recompression.
- The same video is used by Li post-registration iPhone Safari PWA onboarding
  and the public iPhone PWA install/download page.
- Safari: full-screen guide, heading + vertical playable video. No Continue
  button or duplicated copy below the movie.
- If MP4 is missing, stalled or fails: four short UZ/RU/TJ textual steps are
  displayed instead, never a blank or stuck player.
- Other iOS browsers: Li panda and copyable `https://hskai.app/iphone-pwa`
  URL to open in Safari. Do not attempt an automatic Safari launch or pass
  auth/session/referral tokens through a browser handoff.
- Installed standalone PWA, non-iOS clients and existing returning profiles:
  no first-time install dialog. The guide grants no account, Pro, payment or
  notification access; only verified saved onboarding can show it once.
- Share → Add to Home Screen → Add → launch icon. Safari push notifications
  require a separate user permission; installing does not imply consent.

## Required verification

- `python -m unittest tests.test_li_install_video_asset tests.test_li_install_video_route`
- `python -m pytest -q tests/e2e/test_li_onboarding_install.py`
- Test an actual iPhone Safari playback, including byte-range requests, mobile
  viewports, portrait video controls, offline fallback and safe-area layout.
- Check the public `/download` route and Li onboarding use the updated video.
  A successful GitHub import does not itself prove production deployment.
