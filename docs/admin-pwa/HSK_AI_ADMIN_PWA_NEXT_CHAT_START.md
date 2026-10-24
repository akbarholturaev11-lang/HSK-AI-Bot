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
> Жорий runtime/CI checkpoint’ни `MCP_NEXT_CHAT_HANDOFF.md`’дан ол ва GitHub branch HEAD’ни қайта текшир. Documentation commit’лари HEAD’ни ўзгартиради; эски SHA’ни жорий деб қабул қилма. Кунлик кеш `4709c660`да қўшилган. Реал staging, жисмоний қурилма ва ChatGPT уланиши ҳали тасдиқланмаган.
>
> Тайёр ишларни такрорлама: Google/Telegram/passkey login, тўловни transaction-bound WebAuthn билан кўриб чиқиш, V10 UI, OAuth code + PKCE S256 + CSRF consent, token/discovery, consent history/revoke, audit/quota, қисқа token/қайта авторизация, статистика-only MCP ва official SDK regression. Read-only user profile/billing history, AI/course/conversion метрикалари, durable Android intake (0122) ва кунлик статистика кеши ҳам қўшилган. Булар rollout flag’лари билан ЎЧИРИЛГАН.
>
> **База юки бўйича қарор:** PWA ва MCP aggregate статистикаси битта private server-side кешдан ўқийди. Ҳар platform/period учун `generated_at`дан 86 400 секунд ўтгач, биринчи authorized сўровда янгиланади; доимий cron ёки force-refresh йўқ. Мавжуд Redis / `REDIS_URL` ишлатилади; R2 уланмаган. Redis ишламаса, чекланган кунлик кеш ҳар worker’да алоҳида — restart ёки outage пайтида бутун кластерга фақат бир марта ҳисобланади деб ваъда берма. Auth/revoke/audit/quota ҳар сўровда жорий; profile, billing, receipt, access қарорлари ва command’лар кешланмайди. HTTP/SW private no-store сақланади. `READ_PROJECTIONS.md`’ни ўқи.
>
> **Кейинги амалий иш:** inbox read/triage/search, important badge ва default-OFF Apple Push коди GitHub’да тайёр. `d93b75fe`да retained Android JPEG учун private proxy ҳам бор. Android proxy V10 preview’га ҳам уланди: фақат босганда юкланади, ёпилганда object URL ўчирилади, сессия/retention ҳар очишда қайта текширилади. Bot/Release JPEG/PNG/WebP preview ҳам уланди: source+ID ажратилган, canonical owner ва файл reference IO’дан олдин/кейин текширилади. Сервер юкини камайтириш учун фақат босганда юклаш, metadata-only SELECT, worker’га 2 параллел / 30 уриниш-минут ва мавжуд Bot клиент ишлатилади; янги quota DB ёзуви, preload/backfill йўқ. 24 соатлик кешдан чекланган статистика JSON/CSV экспорт ҳам V10’га уланди: source/давр/таърифлар ва асл timestamp сақланади, кеш тайёр бўлса aggregate SQL қайта бажарилмайди. Буни такрорлама. Навбатда қолган first-party бошқарув амалларидан биттасини shared command, аниқ WebAuthn payload, тасдиқ ва audit билан кичик босқичда текшир; sanitized feedback экспорти ҳали алоҳида privacy review талаб қилади. Technical event intake ва қўлланмаган форматлар ҳали алоҳида. `IMPLEMENTATION_PLAN.md`’даги актив рўйхатни текшир. Native intake’дан олдинги йўқ тарихни тўлиқ деб кўрсатма. UI ишларидан олдин `.agents/skills/hsk-ai-ui/SKILL.md` ва `.agents/skills/webapp-testing/SKILL.md`’ни ўқи, V10 услубини сақла. Матнни canonical UZ/RU/TJ’да ёз, генераторни `--write` ва `--check` билан ишлат. Ўзгаришга мос auth/CSRF/owner/replay, backend/PostgreSQL ва browser regression текширувларини бажар. Реал ChatGPT ва ташқи TLS/provider текширувлари алоҳида рухсатли staging босқичида қолади.
>
> Учала flag: `ADMIN_PWA_ENABLED=false`, `ADMIN_PWA_MCP_ENABLED=false`, `ADMIN_PWA_MCP_TRANSPORT_ENABLED=false` бўлиб қолсин. `main`’га merge, production deploy, OAuth secret/клиент созлаш, live ChatGPT улаш, фойдаланувчи ёки тўлов ёзиш рухсатини бериш ЙЎҚ — алоҳида мендан тасдиқ олиш керак. Эски Telegram `/admin.html`, Direct/Play Android ва ҳақиқий бизнес логикасини бузма.
>
> Режа билан тўхтаб қолма: мавжуд реал кодни текшириб, **навбатдаги хавфсиз кичик код босқичини** бажар; CI’дан кейин commit/push фақат шу feature branch’га. `MCP_NEXT_CHAT_HANDOFF.md`’ни янги аниқ натижалар билан янгила. Ҳар ишдан кейин ўзгарган файллар, SHA, CI run, ҳақиқий тест натижалари, қолган блокерларни аниқ бер. Маълумот тўлиқ бўлмаслиги мумкин бўлса, тўғрисини айт.

## Useful links
- [Current MCP handoff](MCP_NEXT_CHAT_HANDOFF.md)
- [MCP connection/security contract](MCP_CONNECTION_CONTRACT.md)
- [Original V10 design reference](ADMIN_PWA_V10_UI_REFERENCE.md)
- [Current PR #201](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/pull/201)
- [Daily-cache runtime Admin PWA/PG/browser CI](https://github.com/akbarholturaev11-lang/HSK-AI-Bot/actions/runs/40086916174)

**Older content referring to PR #200, `codex/admin-pwa`, or missing OAuth consent UI is history, not an instruction to recreate it.**
