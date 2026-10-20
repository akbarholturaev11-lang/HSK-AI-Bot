# Local-first browser assets and skip-test contracts

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

## Fix

- Allow only the three required public JavaScript assets by name; retain the
  private lesson/exam JSON routes and fixed curriculum-map allowlist.
- Permit the bounded locked-lesson question projection after signed identity,
  selected canonical level, lesson bounds, foundation and shared non-consuming
  entitlement checks. Full content/start keep their sequence guard. Reading
  test questions neither unlocks progress nor consumes an allowance.
- Route independent analytics sessions into the existing SQLite API fixtures.

## Risk

The skip-test response retains its existing six-question projection and shared
access decision. Do not extend this exception to full lesson content, progress,
paid access, trial terms or arbitrary public lesson files.

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
