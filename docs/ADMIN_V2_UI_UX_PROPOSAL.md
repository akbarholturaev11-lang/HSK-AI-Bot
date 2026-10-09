# HSK AI Admin V2 — UI/UX migration proposal

Status: UX prototype and implementation specification; not connected to production. Prepared 2026-10-08.

## Evidence
- Existing `app/static/admin.html` has five tabs (dashboard, statistics, users, payments, settings) and embedded HTML, CSS, JS.
- Existing `app/services/admin_miniapp_service.py::_modules()` lists 19 administrative modules.
- Additional inline settings contain AI model selection, notification templates, ad creatives and placements.
- Current frontend contains a narrow drawer for complex operations and a long statistics page.

## New information architecture
1. **Overview**: KPIs, pending payment review, alerts, quick actions.
2. **Analytics**: period-based funnel, Android/Mini App/Desktop, retention, AI tokens and costs.
3. **Users**: ID/username search, user details, subscription management, individual messaging, dangerous user deletion.
4. **Finance**: payment review, Pro pricing, HSK 3.0 unlock pricing, payment methods/QRs, portfolio separated by currency.
5. **Product**: HSK 2.0/3.0, entitlement rules, FREE/TRIAL quotas, trial anti-abuse report, course audio, sales A/B testing.
6. **Marketing**: broadcasts, bot advertising messages, Mini App and app promotions, discounts, reminder templates, release feedback, partners.
7. **System**: AI provider/model, mandatory channels, help/admin contact; proposed audit trail requires backend work.

Mobile bottom navigation: Overview, Analytics, Users, Finance, Menu. Menu exposes all centers; desktop sidebar exposes seven directly.

## Interaction contracts
- Payment review: show method/currency/amount/account/receipt and current status, warn that payment must be verified through bank before granting access. Guard against duplicate submit.
- User deletion: navigate via individual profile and require impact preview, user ID confirmation and permission check.
- Broadcast: audience → message/media → TJ/RU/UZ previews → test send → explicit final delivery.
- Product: 3.0 one-time unlock does **not** unlock full Pro lessons; FREE/TRIAL quotas and anti-abuse guards remain authoritative on server.
- Price editing: show previous/new price, currency, scope and confirm; the HSK 3.0 unlock price is a separate product.
- Metrics: verified data only; show unavailable instead of invented zero; preserve denominator, currency and freshness context.
- Account transitions and payments must be tested against current backend invariants before any release.

## Prototype design direction
- Responsive admin-specific dark UI: background #0c1118, surface #151e2a, border #293543, text #edf1f6, accent #e65d4f; reduce excessive borders and badge decoration.
- Complex flows use full pages or multi-step overlays; short detail previews may use drawers.
- Desktop sidebar and tables; mobile bottom navigation and readable cards; 320px minimum viewport smoke coverage.
- Keyboard search, visible focus, minimum 44px production touch targets, WCAG contrast checks, loading/error states.

## Delivery plan
1. Create component and API inventory; map every existing function to exactly one authoritative owner.
2. Introduce design tokens and router under an **admin-only opt-in feature flag**.
3. Port read-only Overview and Analytics first.
4. Port Users and Finance with full authorization, payment, and deletion regression tests.
5. Port Product, Marketing and System without changing business logic.
6. Run mobile 320/390, tablet and desktop accessibility/end-to-end checks in Telegram WebView and browsers.
7. Review and merge only after production data and critical flows are verified; preserve V1 rollback.

## Prototype artifact
A standalone interactive HTML prototype is produced in the related ChatGPT conversation as `hsk-admin-v2-prototype.html`. It is not yet included in this Git branch. All metrics, users, and operations in it are explicit demo-only examples. No backend API calls or production changes.

## Explicit non-goals
- No main branch change or deployment in this UX stage.
- No alterations to payment calculation, Trial risk thresholds, quotas, access entitlements or ad eligibility.
- An audit log is proposed, not presumed to exist.
