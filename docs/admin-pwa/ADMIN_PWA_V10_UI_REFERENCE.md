# HSK AI Admin PWA — V10 demo source audit (design reference only)

Verified against the existing conversation-mounted file `/mnt/data/hsk-ai-admin-ux-demo-v10.html` on 2026-10-23. **Not a GitHub repository file** and **not published**. The original needs to be provided to the implementation workspace before visual porting.

- Size: **184,575 bytes**
- SHA-256: `8cd9375dd2ef7c27e9f17904000629060139ffb21c667a83c60b282ec321a9b9`
- Inline HTML/CSS/JS, no external API calls (`fetch(` absent). It contains `v6Demo` synthetic data and a visible demo disclaimer; every number and action is browser-only, not a legitimate backend source.
- `<main>` includes `#subtabs`, `#content`, mobile scroll hint. The drawer uses `#overlay`, `#drawerTitle`, `#drawerContent`, `#drawerFoot`, and the mobile navigation is `#mobileTabs`.
- Main view render functions: `renderHome` (~line 515), `renderStats` (~638), `renderUsers` (~656), `renderPayments` (~666), `renderPrices` (~671), `renderMethods` (~673), `renderPortfolio` (~675), `renderFeatures` (~678), `renderCourse` (~680), `renderMarketing` (~692), `renderSystem` (~711).
- Inbox UI: `renderInboxResults` (~753), `renderInboxDrawer` (~757), `openInbox` (~777). Inbox header should stay concise; previous V10 removed redundant heading/description and demo notification footer text.
- All line numbers are landmarks only, not stable contract or CSS selectors.

## Safe porting rule

1. Obtain and check **the exact source hash** (or treat a new provided demo as a deliberate design revision).
2. Extract reusable visual components and view structure; **do not copy** `v6Demo` or fabricated payments/users/feedback, mock mutation handlers, success toasts, or internal demo-only state as real product behavior.
3. Render server responses from `/api/admin/v1/*` through an authenticated, read-only projection first. Every section must have loading/empty/error/unsupported/expired-session UI, and navigation should remain responsive.
4. Use canonical UZ/RU/TJ catalog for permanent UI strings; consult `.agents/skills/hsk-ai-ui/SKILL.md` and `.agents/skills/webapp-testing/SKILL.md`.
5. Wire no privileged mutation until per-transaction WebAuthn verification, server validation and audit logs exist.
6. Keep existing Telegram Admin Mini App untouched.

**Status:** source inspected; no HTML copied into branch, no PWA frontend implemented yet.
