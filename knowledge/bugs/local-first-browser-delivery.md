# Local-first browser assets, catalog ownership and skip-test contracts

## Cause

The private lesson-route migration kept a fixed public asset allowlist but
omitted the two generated UI catalogs and the P3 reservation helper. File-based
browser mocks served those files anyway, hiding real HTTP 404 responses and a
lesson-start `ReferenceError`. The skip-test endpoint also copied the full
lesson sequence guard, although its existing UI and native counterpart offer
tests for locked lessons. Source audits incorrectly required this regression.

The Desktop and Android API tests injected SQLite request sessions while
conversion and entitlement-shadow analytics retained global application
sessions. A denied consuming request could therefore escape the test fixture.

Centralizing only the main dictionaries left handler/formatter/helper locale
maps outside their canonical sources. Editing a shared catalog then did not
necessarily change the displayed copy. Stale browser asset tokens could also
retain an old helper after a correct source update. Tests pinned to former
inline literals could mistake a valid catalog lookup for a missing feature;
one asset test additionally appended `app/static` twice to an already static
root.

## Fix

- Allow only the three required public JavaScript assets by name; retain the
  private lesson/exam JSON routes and fixed curriculum-map allowlist.
- Permit the bounded locked-lesson question projection after signed identity,
  selected canonical level, lesson bounds, foundation and shared non-consuming
  entitlement checks. Full content/start keep their sequence guard. Reading
  test questions neither unlocks progress nor consumes an allowance.
- Route independent analytics sessions into the existing SQLite API fixtures.
- Keep Bot fixed copy in its canonical namespace: 658 own messages and 41
  common/course references per locale, including 98 static Bot maps, 11 dynamic
  templates, profile rendering and 64 backend fixed maps. Entitlement copy is
  display-only; access predicates, limits and interpolation values stay intact.
- Give Mini App inline/helper copy its own bundled namespace and retain exact
  compatibility fallbacks. Required helper bundles use the explicit public
  asset allowlist; source lessons and graded data stay private.
- Validate all 53 generated artifacts together. Refresh content-hash cache
  tokens only on already reviewed HTML; reject unrelated source drift before
  updating the review hash.

## Risk

The skip-test response retains its existing six-question projection and shared
access decision. Do not extend this exception to full lesson content, progress,
paid access, trial terms or arbitrary public lesson files.

Dynamic course/graded material, campaign content, admin-only copy and provider
metadata are not fixed learner UI catalogs. Preserve their producers and
business constants. Source/catalog checks do not prove final CI, authenticated
staging/account behavior or installed-device acceptance.

## Prevention

- `tests.test_telegram_sdk_asset` collects script/stylesheet URLs from HTML and
  requests their exact bytes through the actual FastAPI application, with no
  static file router substitution. It also checks private/unknown-file 404s.
- Backend CI runs that HTTP test on route, HTML and browser-asset changes.
- `tests.test_i18n_miniapp_reservation_asgi` checks an entitled locked target,
  access denials, bounded output, no quota/progress side effect, and unchanged
  full content/start rejection. Both source audits guard this distinction.
- Desktop/Android denied-allowance regressions verify `limit_hit` in fixture
  SQLite, including canonical account ownership. Local app-import checks use
  synthetic credentials and a loopback-only database URL; never inherit a real
  application database for a mocked test.
- `scripts/i18n_build_all_catalogs.py --check` catches stale local artifacts
  and reviewed browser cache tokens without writing source files.
- `scripts/i18n_ui_adoption_audit.py` checks the 79 individually classified
  Python maps in `localization/review/ui_map_exceptions.json`; new unclassified
  maps and stale hash/count exceptions fail. Fixed learner UI belongs in a
  canonical catalog rather than a broad exemption.
- Source-text regressions inspect effective generated catalogs after copy
  migration. Keep callback, entitlement, payment and ad-policy assertions;
  execute the actual local JavaScript module when checking delivered behavior.
  Limit-sheet regressions retain signed server-owned reasons, the existing
  Pro-only CTA and close/back behavior without restoring obsolete trial/ad
  entry points.

## Narrow desktop navigation after upstream UI integration

- Cause: the desktop breakpoint starts at 900px but centers against a fixed
  940px shell; the incoming glass navigation had x=-8px at 900px.
- Fix: clamp its left edge to 12px while retaining the wider course-column
  alignment. No routing, paid access or learning behavior changes.
- Prevention: the existing real-browser glass navigation test now checks
  900/916/940/1280px as well as the original mobile view. It failed at x=-8px
  before the fix. Main's navigation/preload/modal/spacing tests remain in CI.
