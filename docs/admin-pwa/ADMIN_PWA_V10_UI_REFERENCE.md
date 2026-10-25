# HSK AI Admin PWA — supplied V10 visual reference

Current owner-supplied source, received 2026-10-24:
`/Users/kaijimima1234/Downloads/hsk-ai-admin-ux-demo-v10 2.html`.

- Size: **182,765 bytes**.
- SHA-256: `1ff92bf82126ea65672ed703f9fff6553982db2f08f7c1ed2a06396cb6c89566`.
- Its filename says V10; its document title still says V9.
- Inline HTML/CSS/JS, no external fetch or external script dependency.
  Synthetic arrays, notification counts and mutation handlers are visual/demo
  fixtures only, never business logic or an authorized data source.
- Original source and desktop/390px mobile rendering were inspected before
  porting. Slate sidebar, cards, fixed SVG paths, drawers and mobile navigation
  supply the visual language. No complete demo HTML or demo dataset is shipped.

The branch now has a separate public shell using protected real-data APIs,
canonical UZ/RU/TJ text, native passkey enrollment/login and single-editor payment
review. Toolbar period/filter/bell share one row. Unsupported management
features stay disabled; unavailable telemetry remains unavailable. See
`BROWSER_UI_CONTRACT.md` for source paths, exact behavior and QA boundaries.

Skills actually read/applied: repository `.agents/skills/hsk-ai-ui/SKILL.md`,
`.agents/skills/webapp-testing/SKILL.md`, available local `frontend-design` and
`playwright`. Missing demo patterns were auth, confirmation and offline/error/
expired states; the port uses restrained cards/drawers with explicit states,
keyboard/modal support and mobile safe areas. Browser screenshots are synthetic
QA evidence, not real customer/payment records or physical biometric evidence.

## Historical reference

The earlier conversation-mounted `/mnt/data/hsk-ai-admin-ux-demo-v10.html`
was inspected on 2026-10-23: 184,575 bytes, SHA-256
`8cd9375dd2ef7c27e9f17904000629060139ffb21c667a83c60b282ec321a9b9`.
It was unavailable in the implementation workspace until the owner supplied
the revised file above. Earlier absence/source-line notes in the append-only
handoff describe that checkpoint; do not ask for the original again.

## Continuing rule

Keep the verified visual components; never copy demo fixtures or success
handlers. Render actual bounded server projections with clear loading/empty/
error/offline/expired/unavailable states. All privileged commands require their
own audited adapter, server validation, exact one-use WebAuthn from the original contextual action. Existing Telegram `/admin.html` and authentication remain intact.
All three rollout defaults stay OFF. The owner authorized tested intended-code
promotion to main; current remote evidence is in `MCP_NEXT_CHAT_HANDOFF.md`.
No manual deployment or flag activation is included.
