# P3 end-to-end local QA without Railway

The purpose is to run the **actual full HSK AI FastAPI + Telegram bot**
(`app.main:app`) on the exact working code snapshot derived from
`codex/p3-main-integration-20261020` at `b5f4351dfc282f556e333bcc67689dbb39eb0a03`,
with independent local PostgreSQL/Redis and a **dedicated test Telegram bot**.

This is not the anonymous `app.staging_qa:app` partial HTTP-only preview.
It starts course, practice, subscription backend and normal bot polling,
but it has a completely **empty QA database** and paid AI/OAuth/push turned off.
Desktop/Android apps must separately point to this QA origin for installed-client
testing. The QA branch does not incorporate future P3 changes automatically.

## Safety (must not be bypassed)
- Do **not** use production `DATABASE_URL`, bot token, payment integrations, production storage, API keys or database backup. There is no production-data mirror here.
- Before starting, the runtime performs a Telegram `getMe` identity check and
  only accepts the separately approved test bot **@Gentss_3bot**. A production
  token with another bot identity is refused before bot polling.
- Database must be `hsk_p3_local_qa` on service `postgres:5432`; Redis must
  be `redis://redis:6379/0`. Neither service exposes host ports.
- An empty QA schema is initialized through the already reviewed
  `scripts/qa_standalone_bootstrap.py` functions, baseline stamp at
  `0102_payment_review_preview` **only on a verified empty QA database**, then
  normal migrations to `0109_public_site_traffic_daily`. A partial or unknown
  schema is refused, not deleted, guessed or reset.
- OAuth, OpenAI/Gemini paid calls, FCM, native app wakeups, desktop download
  releases and production feedback notification chat are disabled by default.
  This means provider/push/paid AI acceptance remains pending until separately
  provisioned **QA-specific** credentials are configured and reviewed.
- Docker binds the browser port to `127.0.0.1:18080`. Tunnel access, if enabled,
  is external; use test-only users and do not share the URL publicly.

## 1. On a Mac with Docker Desktop and Git

```bash
git clone --branch codex/p3-offrailway-local-qa-20261023 --single-branch \
  https://github.com/akbarholturaev11-lang/HSK-AI-Bot.git
cd HSK-AI-Bot
cp ops/p3-local-qa/env.example .env.p3-local-qa
openssl rand -hex 24
```

Edit `.env.p3-local-qa` **locally**: replace `P3_QA_DB_PASSWORD` with
the generated hex string and `P3_QA_BOT_TOKEN` with the real token for
**@Gentss_3bot only**. Do not paste secrets into ChatGPT or commit them.

```bash
docker compose --env-file .env.p3-local-qa \
  -f ops/p3-local-qa/compose.yml up --build -d

docker compose --env-file .env.p3-local-qa \
  -f ops/p3-local-qa/compose.yml ps

curl --fail --silent --show-error http://127.0.0.1:18080/health
```

Expected successful response: `{"status":"ok"}`. On the Mac browse
`http://localhost:18080/course-v3.html` (real Telegram auth isn't available
in a regular browser). Other public routes can be checked without Telegram.

Use logs to diagnose any failure:

```bash
docker compose --env-file .env.p3-local-qa \
  -f ops/p3-local-qa/compose.yml logs --tail 80 bootstrap api
```

The first fresh-database bootstrap runs once. Subsequent startups verify the
saved schema head and reuse QA test data. If bootstrap fails, do not simply
erase the volume or force a stamp: inspect the error first.

## 2. Real Telegram Mini App on iPhone/Android

For a physically installed Telegram WebView, the test bot must link to a
publicly reachable **HTTPS** test origin, not `localhost`.

1. On the Mac, run a temporary HTTPS tunnel, e.g. with
   `cloudflared tunnel --url http://localhost:18080`.
   Record the printed temporary `https://...trycloudflare.com` origin.
   Cloudflare Tunnel is optional; an independent HTTPS server works too.
2. Set `P3_QA_PUBLIC_ORIGIN` in the **local** `.env.p3-local-qa` to that
   HTTPS origin **without** `/course-v3.html` or a trailing slash.
3. Recreate the app service with the new origin:
   ```bash
   docker compose --env-file .env.p3-local-qa \
     -f ops/p3-local-qa/compose.yml up -d --force-recreate api
   ```
4. Set the test bot **@Gentss_3bot**'s Mini App/menu URL in BotFather to
   `https://YOUR-QA-HOST/course-v3.html` (do not change the production bot).
5. Open the test bot inside Telegram and verify course, practice, voice,
   league/rating and profile tabs. Use freshly created QA users.
6. With actual QA accounts, test UZ/RU/TJ UI copy, HSK 2.0/3.0 course
   selections, lesson open/complete/next, quiz/hw scoring and progress,
   Free/Trial/Pro restrictions, HSK3 unlock and payment *review state*
   using test-only records. Never submit a real payment.
7. Test retries, back navigation, signed Telegram initData, locked/private
   content and offline-reopen handling. Compare before/after account and
   progress in the **QA DB only**.

The HTTPS tunnel is a temporary test exposure; there is no permanent public
deployment. On app restart/cloudflared rotation the origin may change.

## 3. Android + Desktop cross-client acceptance

Hosting the backend does **not** rebuild Android APK, macOS app or Windows EXE.
Build dedicated QA variants from this snapshot and configure their backend
origin to the same public HTTPS QA domain. See
`docs/UNIVERSAL_NATIVE_ACCOUNT_QA.md`, including Android
`-PPOMP_QA_API_ORIGIN=https://YOUR-QA-HOST` and the QA protocol
`pomp-hsk-ai-qa`. The QA Android/desktop clients use their own
package/bundle IDs and must not replace installed production clients.

Real Google/Apple OAuth, upstream AI Voice, push notifications and automatic
native return require **separate registered QA credentials/callbacks** and
explicit review of the launch guard. They are intentionally unavailable in
this initial no-production-secret mode. Neither database fixture tests nor
local browser UI smoke prove all these acceptance gates.

## Stop / resume

```bash
docker compose --env-file .env.p3-local-qa \
  -f ops/p3-local-qa/compose.yml down
```

This stops only `hsk-p3-local-qa` services and retains its QA database volume.
Never use `down --volumes` without intending to permanently erase QA records.
Deleting the QA database is **not** part of setup. Keep this separate branch
out of `main`/production until external acceptance is complete.

## Smoke/verification status

The code in this QA branch is the P3 application tree plus Docker/QA
bootstrap/guard/tests/docs only. The remote GitHub API can check the files,
but this authoring environment has neither Docker nor a local clone of
the complete repository. **Docker build, migrations, polling, device tests and
HTTPS tunnel are not claimed as executed here.** On the Mac they are the
necessary practical acceptance steps.
