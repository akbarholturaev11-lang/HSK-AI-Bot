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

## Owner-supplied revision — 2026-10-24

The owner supplied `/Users/kaijimima1234/Downloads/hsk-ai-admin-ux-demo-v10 2.html`
(182,765 bytes), SHA-256
`1ff92bf82126ea65672ed703f9fff6553982db2f08f7c1ed2a06396cb6c89566`.
The filename says V10 while its document title still says V9. Treat this as the
new visual reference; the prior hash above is historical. The original was
rendered at desktop and 390px mobile sizes before porting. No external fetch
or external script dependency was found. Its demo data/handlers remain untrusted.

The branch now ports its slate sidebar/cards/drawers/mobile navigation and
compact header controls into a separate public shell. Only CSS and fixed SVG
paths are copied; actual data, authorization and decisions use existing audited
APIs. Additional auth/confirmation/offline states follow the skills actually
read: repository `hsk-ai-ui`, `webapp-testing`, local `frontend-design` and
`playwright`. See `BROWSER_UI_CONTRACT.md` for exact behavior and QA boundaries.
The whole demo HTML is not committed; no demo dataset is shipped.
