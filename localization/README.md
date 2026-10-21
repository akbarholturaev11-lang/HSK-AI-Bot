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
52 generated artifacts. Browser course bundle URLs also require their existing
Git-blob content hash; keep all twelve HTML consumers in sync.

| Authoring source | Local consumer |
| --- | --- |
| `ui/{uz,ru,tj}/common.json` | Shared Android, browser, Desktop and Bot UI |
| `ui/{uz,ru,tj}/course.json` | Existing course and Mini App UI; platform bundles |
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

## Remaining adoption at this checkpoint

The full Desktop dictionary, Bot `TEXTS`/`COURSE_I18N`, all 36 native XML files,
fixed notification surfaces, public-page content, and all 18 registered Mini App
dictionaries have canonical sources. Further Bot handler/formatter locale maps
and the remaining Mini App inline/helper maps are still being migrated. The
short active checkpoint is `RESUME_NEXT_CHAT.md`; do not repeat completed UI.

Dynamic campaign/user/AI copy, Chinese course and graded answer data are not UI
catalogs. Preserve their existing producers, source hashes, access and identity.
Actual staging/accounts, installed clients and release authorization remain
separate from this deterministic source build.
