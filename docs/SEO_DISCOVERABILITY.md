# HSK AI public SEO — implementation and deployment report

Status: implemented locally; no commit, push, deployment or search submission performed.

## A. Audit before implementation

- Backend: FastAPI in `app/main.py`; aiogram bot and DB/background jobs share its lifespan. No Flask server.
- Railway: `railway.toml` → `scripts/start.sh` → Alembic upgrade → Uvicorn; health check remains `/health`. Procfile also targets `app.main:app`.
- No root product landing, `/tj/`, `/ru/`, `/uz/`, robots, sitemap, IndexNow or Search Console verification configuration existed.
- Mini App HTML had a generic HSK AI title and interactive content; the desktop download page had its own title/description, but no multilingual public product SEO inventory.
- Verified product evidence: `app/main.py` course/voice/practice routes, `app/static/course_v3_data/` HSK 1–4 materials and exams, `app/services/course_v3_dictionary.py` TJ/RU/UZ, `app/services/voice_practice_service.py`, `app/services/course_miniapp_analytics_service.py` progress. No fabricated student counts, ratings, results or certification claims.
- Existing analytics require a verified Telegram ID and affect learner activity; anonymous visitors must not be inserted as fake learners.
- Existing bot username helper defaults to `darsi_chini_bot`. Marketing CTA explicitly targets the user-requested `https://t.me/darsi_chini_bot` without adding a referral/start payload.
- `codex/local-ai` is checked out in another worktree. No branch was switched/reset and no unrelated work was modified.

## B. Implementation files

- `app/api/public_site.py`: isolated router, robots/sitemap, fixed-destination CTA redirect, bounded campaign logging, optional verification file, asset allowlist.
- `app/public_site/content.py`: all seven pages and localized copy, maintained canonical inventory.
- `app/public_site/render.py`: escaped server HTML, canonical/hreflang, JSON-LD, social metadata and verification meta tags.
- `app/public_site/__init__.py`: package boundary.
- `app/static/public-site.css`: responsive public-page styling; existing Mini App CSS untouched.
- `app/main.py`: one import and one router registration.
- `app/config.py`, `.env.example`: optional SEO environment settings.
- `scripts/submit_indexnow.py`: dry-run-first, manually invoked IndexNow tool.
- `scripts/preview_public_site.py`: isolated preview without production bot/DB startup.
- `scripts/check_public_site_browser.py`: mobile/desktop/no-JS/CTA smoke.
- `tests/test_public_site.py`: route/HTML/crawler/tracking/config regression tests.
- `PROJECT_MEMORY.md`: important architecture and config note.
- `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`: regenerated code graph (may include other concurrently present workspace changes).
- `docs/SEO_DISCOVERABILITY.md`: this report and deployment runbook.

Existing brand avatar/cover are reused, not regenerated. No DB migration or payment/course/Telegram SDK changes.

## C. Public URLs

Set `PUBLIC_SITE_URL` to the final HTTPS origin, without path/query/trailing slash. If empty, the origin is derived from `MINI_APP_BASE_URL`, never from request Host headers.

Current repository default origin (configuration evidence, not a live deployment confirmation):
`https://telegram-chinese-bot-production.up.railway.app`

- `https://telegram-chinese-bot-production.up.railway.app/`
- `https://telegram-chinese-bot-production.up.railway.app/tj/`
- `https://telegram-chinese-bot-production.up.railway.app/ru/`
- `https://telegram-chinese-bot-production.up.railway.app/uz/`
- `https://telegram-chinese-bot-production.up.railway.app/tj/hsk/`
- `https://telegram-chinese-bot-production.up.railway.app/tj/learn-chinese/`
- `https://telegram-chinese-bot-production.up.railway.app/tj/ai-chinese-teacher/`

Root is a distinct Tajik product/language entry page with its own canonical and x-default alternate. `/tj/`, `/ru/`, `/uz/` are reciprocal home variants. Tajik uses ISO language code `tg`, while URLs retain requested `/tj/`. Intent guides are unique Tajik articles with self hreflang only; unrelated pages are not falsely marked as translations. No RU intent duplicates were needed.

## D. Page title and description

| Path | Title | Meta description |
|---|---|---|
| `/` | HSK AI — забони чинӣ дар Telegram | HSK AI: платформаи омӯзиши забони чинӣ бо ёрии AI. Бо тоҷикӣ оғоз кунед ё русӣ ва ӯзбекиро интихоб намоед. Курсҳои HSK 1–4 дар Telegram. |
| `/tj/` | Омӯзиши забони чинӣ ба тоҷикӣ — HSK AI | Забони чиниро ба тоҷикӣ бо HSK AI омӯзед: курсҳои HSK 1–4, шарҳи AI, машқи талаффуз, луғат ва тестҳо дар Telegram Mini App. |
| `/ru/` | Китайский язык для таджиков — HSK AI в Telegram | HSK AI — китайский язык с объяснениями на таджикском, русском и узбекском. Курсы HSK 1–4, AI-помощник, произношение, словарь и тесты в Telegram. |
| `/uz/` | Xitoy tilini o‘rganish — HSK AI Telegram kurslari | HSK AI bilan xitoy tilini o‘rganing: HSK 1–4 kurslari, AI yordamchi, talaffuz mashqi, lug‘at va testlar. Tojik, rus va o‘zbek tillarida Telegram’da. |
| `/tj/hsk/` | HSK ба тоҷикӣ: курсҳои HSK 1–4 — HSK AI | Барои омӯзиши HSK ба тоҷикӣ аз куҷо оғоз кунем? Роҳнамои интихоби маводи HSK 1–4, машқи калимаҳо ва такрори дарсҳо дар HSK AI. |
| `/tj/learn-chinese/` | Омӯзиши забони чинӣ аз сифр ба тоҷикӣ — HSK AI | Забони чиниро аз сифр оғоз кунед: пинйин, оҳангҳо, иероглиф ва ҷумлаи аввал. Роҳнамои кӯтоҳи тоҷикӣ бо намуна ва машқи мустақилона. |
| `/tj/ai-chinese-teacher/` | Ёрдамчии AI барои забони чинӣ ба тоҷикӣ — HSK AI | Аз AI барои омӯзиши чинӣ чӣ гуна истифода барем? Намунаи саволҳо ба тоҷикӣ, таҳлили ҷумла, машқи овозӣ ва санҷидани ҷавобҳои AI дар HSK AI. |

## E. robots.txt

`GET /robots.txt` returns text/plain. Identical rules are applied to `*`, `Googlebot`, `Bingbot`, and `OAI-SearchBot`:

- `Disallow: /` as the default.
- Explicit exact-path allows for seven public HTML pages, including their query variants.
- Allow `/public-assets/`, `/robots.txt`, `/sitemap.xml`.
- Allow only the configured IndexNow ownership key file when enabled.
- `Sitemap: <PUBLIC_SITE_URL>/sitemap.xml`.

This excludes admin, APIs, payments/subscription, internal course data, Mini App, uploads, docs, CTA redirect and future unlisted paths. These are crawl preferences, not access control: existing auth is unchanged. If a private URL is already indexed, handle removal/noindex separately; robots disallow alone does not guarantee removal. Existing desktop download URL remains usable but is deliberately outside this SEO inventory.

## F. sitemap.xml

`<PUBLIC_SITE_URL>/sitemap.xml` contains exactly the seven self-canonical public HTML URLs, no query strings, redirects, keys, admin, APIs, payments or Mini App. No artificial lastmod: content dates are not currently maintained. Add lastmod only when real editorial dates are tracked.

## G. Structured data and social previews

Every page: Organization, WebSite, SoftwareApplication (`applicationCategory: EducationalApplication`), WebPage. `/tj/hsk/` additionally has four Course entities for the actual HSK 1–4 materials, anchored to visible sections.

Organization `sameAs` and application `installUrl` reference the Telegram bot; website URLs remain website URLs. No offers/prices, ratings/reviews, exam guarantees or invented durations. This describes the product; eligibility for Google rich results is not promised.

Every page has unique OG title/description/url, `og:type=website`, OG image, image alt, Twitter title/description/image and `summary_large_image`. Existing brand cover is served as `/public-assets/social-cover.webp` (square source; preview services may crop it).

## H. Telegram CTA tracking

- `GET` HTML requests emit `landing_view` (HEAD requests do not).
- `/go/telegram?page=<allowlisted-page>&...` emits `telegram_bot_cta_clicked`, then HTTP 302 to the fixed requested bot. No open redirect; no bot message is sent.
- `source`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content` are allowlisted, cleaned and capped to 80 characters each.
- Internal page/language/guide links and CTA carry those tags. Browser-back URLs retain them. No cookies, localStorage, cross-session identifier or Telegram identity correlation.
- Arbitrary query values, initData, user ID and referrer are not copied into analytics events. No campaign values enter JSON-LD/canonical/sitemap. Do not put secrets or personal information in campaign labels; standard proxy/Uvicorn access logs can retain requested URLs.
- Event sink is `uvicorn.error.public_analytics` at INFO, which inherits the configured Uvicorn error logger, visible in Railway logs as `public_site_event {JSON}`. No DB migration, synthetic Telegram ID, learner activity mutation or public write API.
- These are request/click counts, including refreshes, crawlers and possible automated requests. They are NOT unique people, verified bot starts or conversions. Do not divide raw log totals and claim student conversion. For durable reporting configure a log drain/retention and bot filtering. Authenticated end-to-end attribution is a separate future task.

## I. Validation

See the final validation results below. Tests run against the isolated router without contacting Telegram, payment systems or production DB. The full existing test suite covers course/quiz/homework/access/payment contracts; browser smoke covers only the new public pages.

Reproduce:

```bash
python -m pytest tests/test_public_site.py -q
python -m pytest tests -q
python -m compileall -q app/public_site app/api/public_site.py app/main.py app/config.py scripts/submit_indexnow.py
python -m uvicorn scripts.preview_public_site:app --host 127.0.0.1 --port 8765
# In a second terminal (Playwright + Chromium required):
python -m scripts.check_public_site_browser
```

## J. After deployment — manual checklist

1. Choose the stable public domain before submission. Set `PUBLIC_SITE_URL=https://<public-domain>` in Railway. Keep `/health`, start command, DB and bot configuration unchanged. For a custom domain attach DNS and HTTPS in Railway. No DNS or deployment changes have been made by this task.
2. Deploy reviewed changes, then GET `/`, `/tj/`, `/ru/`, `/uz/`, all three TJ guides, `/robots.txt`, `/sitemap.xml` and the OG image. Check rendered source, canonical origin, HTTPS, redirects and mobile CTA. Repeat with Googlebot, Bingbot and OAI-SearchBot user agents; ensure any CDN/WAF permits real crawler IPs. Staging should be protected outside this production crawl configuration.
3. Google Search Console: create a Domain property via the DNS token supplied by Google, or URL-prefix property using `GOOGLE_SITE_VERIFICATION` (meta-token value only) and redeploy. Do not invent a token. Submit `<PUBLIC_SITE_URL>/sitemap.xml`, inspect `/tj/` and guide URLs, and request indexing. Monitor Pages, canonical selection and Search Performance.
4. Bing Webmaster Tools: import the verified Google property or set the issued `BING_SITE_VERIFICATION` meta value and redeploy. Submit the same sitemap and inspect URLs.
5. IndexNow: generate a random ownership key outside Git (e.g. `python -c "import secrets; print(secrets.token_hex(16))"`), save in Railway `INDEXNOW_KEY`, redeploy, check `https://<public-domain>/<key>.txt` returns exactly the key. This is an intentionally public proof-of-ownership key, not a bot/payment credential. Do not put its value into Git or memory files.
6. From a trusted environment with the same config, run `python -m scripts.submit_indexnow` to review public URLs, then `python -m scripts.submit_indexnow --submit` to notify Bing/participating search engines. Tool verifies the key file before POST, uses TLS/timeouts, does not follow redirects, and accepts only HTTP 200/202. No startup hook or automatic network submission exists. Key rotation requires redeploying the key route before submission.
7. Validate schema with Schema.org Validator and inspect Google Rich Results output; absence of a rich-result type is not a schema failure. Check social preview cropping in the actual share services.
8. Monitor Railway `public_site_event` logs, crawler fetch errors and search impressions. These changes enable discovery but do not guarantee ranking, indexing or ChatGPT inclusion. No separate paid “AI indexing” service is required by this implementation.

Official references used:

- [Google localized pages and hreflang](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Google canonical URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [OpenAI crawler documentation](https://developers.openai.com/api/docs/bots)
- [IndexNow protocol](https://www.indexnow.org/documentation)

## Release feedback draft — not sent

- Release: **HSK AI — шиносоӣ ва роҳнамоҳо ба тоҷикӣ**.
- Announcement: «Саҳифаҳои нави HSK AI омодаанд: шиносоӣ бо курсҳо, роҳнамои оғози забони чинӣ ва истифодаи AI. Саҳифаро кушоед ва гузариш ба ботро санҷед.»
- Changed: public TJ/RU/UZ introductions and three Tajik educational guides; learner course/payment flow is unchanged.
- Test action: «Sinab ko‘rish» → `<PUBLIC_SITE_URL>/tj/`; read the guide, switch language and click the Telegram CTA.
- Target: Tajik-speaking users first; small RU/UZ reviewer segment for their variants.
- Rating: «Саҳифа то чӣ андоза фаҳмо буд? Аз 1 то 5 баҳо диҳед. Чиро беҳтар кунем?»
- Reward text: **Blocked on actual admin choice, not invented.** Before sending, select the real reward/discount supported by the existing Release feedback module and replace `[REWARD]` in «Барои фикру мулоҳизаатон [REWARD] мегиред.»
- After actual grant: «Тавре гуфта будем, [REWARD] ба шумо дода шуд.» Do not use this confirmation unless the reward was successfully granted.
- Metrics: page requests, CTA requests by campaign/language, feedback count, average feedback rating; after indexing, impressions/clicks by query and language. Filter crawler/repeat traffic for acquisition analysis.
- Only send through the existing admin Release feedback module after deployment and explicit admin approval. Nothing has been sent.

## Final validation results (2026-09-09)

- Dedicated SEO tests: **9 passed** (all seven HTML routes, metadata/schema, robots allow/deny boundaries, sitemap inventory, UTM, redirect safety, verification escaping, IndexNow dry-run and ownership checks).
- Existing full suite at validation time: **1271 passed, 3 skipped, 78,155 subtests passed**; four existing Python sqlite datetime-adapter deprecation warnings. The three skipped modules were browser E2E modules before Python Playwright was installed. Two additional IndexNow test cases were subsequently added and included in the final 9-test SEO run.
- Chromium public-page smoke: **7 routes × 3 widths (320, 390, 1440) passed**, no horizontal overflow or console/page errors. JS-disabled educational content and CTA visible, campaign tags preserved across languages, real local CTA 302 inspected without navigating to Telegram.
- `compileall`, `git diff --check`: passed.
- `graphify update .`: completed; graph/report refreshed. HTML graph visualization skipped by graphify because node count exceeds its 5,000-node visualization limit; code graph generation succeeded.
- No production bot, production DB, payment or actual search submission was exercised. No commit/push/deploy performed.
- Unrelated concurrent `app/repositories/user_repo.py` changes were observed and left untouched; full-suite result describes the current shared workspace.

Local screenshot: `/tmp/hsk-seo/mobile.png`. Local preview: `http://127.0.0.1:8765/tj/` while the isolated preview server runs.

### Existing Mini App browser follow-up

After installing Python Playwright, five relevant existing Mini App browser tests were run using the cached Chromium executable (no production services): **4 passed, 1 failed, 66 deselected**.

Passed:
- `test_course_v3_opens_static_map_and_query_lesson_sheet`
- `test_hsk_exam_uses_public_questions_and_server_result`
- `test_subscription_page_smoke`
- `test_subscription_checkout_tracks_one_attempt_through_real_stages`

Existing failure:
- `test_course_v3_support_pages_render_real_static_data`: memorize expects `1/8`, but shows `1/1 — Ma’lumot yuklanmadi`.
- Reproduced the exact failure against a `git archive HEAD` baseline in `/tmp/hsk-seo-head-baseline`, with none of the SEO changes: **1 failed, 70 deselected**. Relevant Mini App static data and test files have no diff against HEAD.
- This is an existing memorize data/fixture-loading issue, not a regression introduced by the SEO router. It was not changed because course logic is outside this task. Follow-up: diagnose memorize standalone fixture/data loading separately.

The committed-to-workspace Python public-page smoke script also passed independently after Playwright installation. Existing homework/result service tests are covered in the full unit/integration suite; no real learner homework or production payment was submitted.
