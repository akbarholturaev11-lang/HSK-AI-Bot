# HSK AI brand mark

The icon is a **knot**: two rounded squares, one turned 45 degrees, woven so
each strand passes over at four crossings and under at the other four — the
Chinese knot that stands for something tied together and continuous. It avoids
the mascot pattern used by most language-learning apps and stays readable down
to a 48px launcher icon.

- Cinnabar ground: `#F0614C` → `#C02F32` (linear, top-left to bottom-right)
- Gold strand: `#F7C948` → `#D9920F` (linear, top to bottom)
- Master vector: `hsk-ai-logo.svg`
- 1024px store/export master: `hsk-ai-logo-1024.png`
- Android ground: `android/app/src/main/res/drawable/ic_launcher_background.xml`
- Android foreground: `android/app/src/main/res/drawable/ic_launcher_foreground.xml`
- Android monochrome: `android/app/src/main/res/drawable/ic_launcher_monochrome.xml`
- Desktop (Tauri) icons: generated from the 1024px master

The under-passes are not gaps in the path. Each strand is drawn full, then cut
by a casing stroke painted in **the same gradient as the ground**, so the cut
reads as the cinnabar behind the knot. That is why the casing gradient in
`ic_launcher_foreground.xml` must stay identical to `ic_launcher_background.xml`
— change one and the knot grows a visible halo. The themed (monochrome) icon
has no ground to borrow, so there the strands carry real gaps instead.

Keep the complete mark inside the central adaptive-icon safe zone. Do not add
`HSK AI`, a Chinese character, a flag, or a mascot inside the launcher icon.
