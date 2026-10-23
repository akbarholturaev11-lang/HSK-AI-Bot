# Android UI resources

Edit native UI text here, then run:

```sh
python3 scripts/i18n_build_android_catalogs.py --write
python3 scripts/i18n_build_android_catalogs.py --check
```

These 36 canonical files generate the corresponding committed Android
`app/src/{main,direct,play}/res/values*/*.xml` files byte for byte. Existing
resource IDs and all consumers remain unchanged. `values` is Uzbek,
`values-ru` Russian and `values-tg` Tajik (`tj` in backend APIs).

Native XML deliberately preserves Android escaping, printf placeholders,
plurals, resource references, nontranslatable brands and Direct/Play overlays.
Shared `hsk_common_i18n.xml` and `hsk_course_i18n.xml` remain generated from
`localization/ui/*/{common,course}.json`; do not duplicate them here.
Do not edit generated native copies directly. The generator validates the
whole batch, including locale/placeholder parity, before writing any file.
P0 and Android CI check generated copies for drift. No runtime translation
request, new locale, billing rule or course-content change is introduced.
