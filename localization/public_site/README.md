# Public-site copy

Author existing localized public-page and navigation copy in `content.py` here.
Run `python3 scripts/i18n_build_public_site_catalog.py --write` to update the
committed `app/public_site/content.py` bundle, then `--check` to verify it.

The existing structured Python content is preserved byte for byte, including
tuple values, legal notices, URL groups, language tags and SEO metadata. The
renderer and public API keep importing the bundled application module. Neither
generation nor page rendering fetches individual translations remotely.
Downloader UI remains owned by the shared course JSON catalog.
