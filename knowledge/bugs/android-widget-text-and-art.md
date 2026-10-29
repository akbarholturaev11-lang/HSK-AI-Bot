# Android widget: illustration and text need separate space

- Cause: a full-frame illustration leaves no safe text area. Removing a dark panel or moving overlay text upward still covers the face. A later failed render can also leave older PNGs in the same test directory.
- Fix: allocate disjoint header/art cells, keep the selected modern transparent panda's aspect ratio, and share the actual native rounded header with the install preview. Use semantic high-contrast colors; no scrim or scene overlay.
- Risk: very small sizes and font metrics can clip captions. Decorative outline copies are not additional semantic text; hidden copies must not be counted as visible clipping.
- Prevention: `WidgetPersonalLayoutTest` measures visible localized text and real panda rectangles at all three sizes/themes, asserts no intersection and verifies the actual counter/font. Use a fresh `widgetQaOutput` per run, require the final successful result and inspect only PNGs from that run. Legacy wording may use its existing max-lines ellipsis; real personal copy has its own non-truncation guard.

## Explicit redraw must advance the observed clock

- Cause: Glance 1.1.1 does not restart an active `provideGlance` on `update`. With unchanged Preferences, a plain `ZonedDateTime.now()` inside skipped composition can leave an expired personal phase visible even after an explicit redraw. Launcher accessibility can also expose widgets on hidden pages; those nodes are not visible host proof.
- Fix: observe an in-process render clock and advance it on coordinator redraw, initial composition, provider update and host resize. Existing expiry/day/zone resolvers then run again without changing stored proof or starting any timer, network call or notification.
- Risk: Android may still display the last RemoteViews until the OS permits another update. This fix does not promise an exact-time alarm or immediate offline revocation.
- Prevention: the QA-only, opt-in `WidgetLauncherTest` uses actual system pin/resize, requires visible nonempty node bounds, expires accepted synthetic proof without changing stored data and checks the real launcher after redraw. It also exercises a real zone/day broadcast, logout/relink, unknown wire data and normal unauthenticated tap with reminders OFF and notification permission denied. Keep synthetic fixture acceptance distinct from real-account, signed-build and provider delivery checks.
