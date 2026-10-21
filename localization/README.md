# Local-first UI authoring

Edit existing UZ/RU/TJ text under this directory, then build the committed local
resources once. Clients and the Bot read their bundled resources; no individual
UI translation needs a runtime server request.

```sh
python3 scripts/i18n_build_all_catalogs.py --write
python3 scripts/i18n_build_all_catalogs.py --check
```

The builder validates every namespace before writing any output, rejects
duplicate output ownership and reports missing/stale bundles. P0 checks all
53 generated artifacts. The unified builder also refreshes existing browser
asset cache tokens using the generated file's Git-blob content hash. It changes
tokens only in already reviewed HTML and updates the corresponding reviewed
hash; unrelated source changes require review first. `--check` reports stale
artifacts or cache tokens without writing them.

| Authoring source | Local consumer |
| --- | --- |
| `ui/{uz,ru,tj}/common.json` | Shared Android, browser, Desktop and Bot UI |
| `ui/{uz,ru,tj}/course.json` | Existing course and Mini App UI; platform bundles |
| `ui/{uz,ru,tj}/miniapp.json` | Mini App inline/helper maps through the bundled `hsk-miniapp-i18n.js`; shared messages retain common/course references |
| `ui/{uz,ru,tj}/desktop.json` | Desktop-specific labels, with shared keys owned by common/course |
| `ui/{uz,ru,tj}/bot.json` | Bot messages and compatibility key tables; shared keys are references |
| `ui/{uz,ru,tj}/notifications.json` | Fixed notification defaults/titles/CTAs; admin/custom campaign copy keeps precedence |
| `android/{main,direct,play}/values*/*.xml` | Native resources, byte-identical IDs/escaping/qualifiers and channel overlays |
| `public_site/content.py` | Existing public-page/SEO content module, byte-identical structured data |
| `lessons/nhsk2_grammar_uz_ru_tj.tsv` | Separately source-bound authenticated display overlays; never public UI bundles |

Native XML and structured public-site Python retain their existing formats to
preserve resource formatting, tuple/route contracts and platform behavior.
Generated application copies are delivery artifacts, not additional authoring
sources. Legacy inline browser/Desktop fallback dictionaries remain during
client rollover; editing one does not replace its canonical catalog value.

## Completed fixed-copy ownership

The full Desktop dictionary, Bot `TEXTS`/`COURSE_I18N`, all 36 native XML files,
fixed notification surfaces, public-page content, and all 18 registered Mini App
dictionaries have canonical sources. Bot ownership now includes **658 own
messages and 41 shared references per locale**, **98 static Bot maps**, **11
dynamic Bot templates**, profile templates, and **64 backend fixed maps**.
Entitlement text formatting resolves local display copy while retaining the
existing access decisions, limits and formatting values. Mini App inline/helper
maps resolve through the separate local Mini App namespace; legacy dictionaries
remain explicit compatibility fallbacks. The short active checkpoint is
`RESUME_NEXT_CHAT.md`; do not repeat completed UI.

The remaining **79 Python locale maps** are individually classified in
`review/ui_map_exceptions.json`. `scripts/i18n_ui_adoption_audit.py` checks their
content-free AST hashes and counts, rejecting new unclassified maps and stale
exceptions. A new learner-facing fixed-copy map belongs in its canonical
namespace rather than an exception. Learning material, graded data, dynamic
campaign content, admin-only copy and provider/locale metadata retain their
existing ownership.

Source-text tests must inspect effective generated catalogs when copy moves out
of a helper. Keep behavioral assertions for callbacks, access/advertising/payment
constants and thresholds; use actual local JavaScript execution where a source
substring no longer represents the delivered behavior.

Dynamic campaign/user/AI copy, Chinese course and graded answer data are not UI
catalogs. Preserve their existing producers, source hashes, access and identity.
Actual staging/accounts, installed clients and release authorization remain
separate from this deterministic source build. This ownership checkpoint does
not establish final CI success or real-account/device acceptance.
