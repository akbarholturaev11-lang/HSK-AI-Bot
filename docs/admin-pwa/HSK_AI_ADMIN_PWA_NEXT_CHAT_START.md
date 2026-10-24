# Start a new ChatGPT / Codex conversation — CURRENT HSK AI Admin PWA MCP

**Status: Draft PR #201, unmerged. Do not revive the old PR #200 payment-refactor handoff.**

## Copy/paste prompt (Uzbek Cyrillic)

> HSK AI Admin PWA — ChatGPT MCP интеграциясини **айнан GitHub’да тўхтаган жойидан амалий давом эттир**.
>
> Репозиторий: `akbarholturaev11-lang/HSK-AI-Bot`
>
> **Фақат иш branch’и:** `feat/admin-pwa-mcp-readonly-20261024`
>
> **Draft PR #201:** https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/201
>
> **Энг биринчи** `docs/admin-pwa/MCP_NEXT_CHAT_HANDOFF.md` файлини тўлиқ ўқи. У ерда охирги текширилган commit, CI, UI/UX skill’лар, код архитектураси ва қолган ишлар ёзилган. Кейин `MCP_CONNECTION_CONTRACT.md`, `HSK_AI_ADMIN_PWA_TEMP_RULES.md`, тарихий handoff’нинг охирги қисмини ва REAL кодни текшир. Эски `CODEX_RESUME.md` PR #200 даврига тегишли, ҳозирги ишни ундан қайта бошлама.
>
> Маълум checkpoint: `38f253d06bda251ecd4f011015650c70adc94ac2` — охирги тўлиқ green код commit; documentation commit’лари кейин SHA’ни ўзгартиради, шунинг учун жорий HEAD’ни GitHub’дан қайта ол. GitHub Actions run https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40076721766: **280 passed / 13 PG-only skipped**, **61 legacy passed**, **13 REAL PostgreSQL passed**; desktop/iPhone consent UI, UZ/RU/TJ, browser/WebAuthn/Service Worker synthetic QA ва 63/0 stale каталоглар тасдиқланган. Реал ChatGPT уланиши ҳали синалмаган.
>
> Ҳозир қўшилганларни такрорлама: OAuth код + PKCE S256 + admin’нинг **CSRF ҳимояланган розилик экрани** (GET/POST `/oauth/authorize`), token алмашиш `/oauth/token`, OAuth discovery, фақат `hskai_statistics` tools/call’ли `/mcp`, Alembic 0118–0120, desktop/iPhone responsive UI ва canonical UZ/RU/TJ. Улар feature flag’лар билан ЎЧИРИЛГАН.
>
> **Кейинги амалий иш:** жорий кодни яна бир марта хавфсизлик аудитидан ўтказ; MCP/OAuth’нинг ҳақиқий ChatGPT client metadata/callback талабларига мослигини расмий спецификациялар билан текшир. Браузерда admin’га consent/grant history + revoke, алоҳида аудит ва rate limiting қўшишдан бошла. Мавжуд `.agents/skills/hsk-ai-ui/SKILL.md` ва `.agents/skills/webapp-testing/SKILL.md`’ни UI ишларидан олдин ўқи. В10 дизайн тилидан чиқма, уч тилдаги матнни каноник файлда ёз, генераторни `--write` ва `--check` билан ишлат. Қатъий auth/CSRF/client/owner/replay ва REAL PostgreSQL regression тестлари бўлсин. Мавжуд кодни чуқур ўқимасдан дубликат механизм қилма.
>
> Учала flag: `ADMIN_PWA_ENABLED=false`, `ADMIN_PWA_MCP_ENABLED=false`, `ADMIN_PWA_MCP_TRANSPORT_ENABLED=false` бўлиб қолсин. `main`’га merge, production deploy, OAuth secret/клиент созлаш, live ChatGPT улаш, фойдаланувчи ёки тўлов ёзиш рухсатини бериш ЙЎҚ — алоҳида мендан тасдиқ олиш керак. Эски Telegram `/admin.html`, Direct/Play Android ва ҳақиқий бизнес логикасини бузма.
>
> Режа билан тўхтаб қолма: мавжуд реал кодни текшириб, **навбатдаги хавфсиз кичик код босқичини** бажар; CI’дан кейин commit/push фақат шу feature branch’га. `MCP_NEXT_CHAT_HANDOFF.md`’ни янги аниқ натижалар билан янгила. Ҳар ишдан кейин ўзгарган файллар, SHA, CI run, ҳақиқий тест натижалари, қолган блокерларни аниқ бер. Маълумот тўлиқ бўлмаслиги мумкин бўлса, тўғрисини айт.

## Useful links
- [Current MCP handoff](MCP_NEXT_CHAT_HANDOFF.md)
- [MCP connection/security contract](MCP_CONNECTION_CONTRACT.md)
- [Original V10 design reference](ADMIN_PWA_V10_UI_REFERENCE.md)
- [Current PR #201](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/201)
- [Verified current-code Admin PWA/PG/browser CI](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40076721766)

**Older content referring to PR #200, `codex/admin-pwa`, or missing OAuth consent UI is history, not an instruction to recreate it.**
