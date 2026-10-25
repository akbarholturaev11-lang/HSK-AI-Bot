# Design

## Context

See the proposal and canonical [handoff](../../../../docs/admin-pwa/MCP_NEXT_CHAT_HANDOFF.md). The supplied HTML is the already verified 182,765-byte V10 reference. The current Home shows four counters and long detail lists; Statistics has seven tabs but several are sparse and Sources is unavailable. `pwa_read.statistics` already provides safe basic aggregates, and `pwa_statistics_cache` provides private daily Redis/R2 snapshots with an eight-second cold-load deadline and read-only five-second SQL deadlines.

Legacy `AdminMiniAppService.overview` is not a safe browser proxy: it loads latest private accounts/payments and unrelated settings; advanced helpers can materialize event/payment history. `AdminFinanceStatsService.build` loads historical approved payments and subscription entry events. Their definitions and appropriate aggregate helpers are reusable, not their entire responses.

## Goals / Non-Goals

**Goals:** Match the reference's Home composition and seven Statistics layouts with actual bounded canonical analytics and complete meaningful controls. Keep the chosen daily-update/load policy, locale ownership and safe commands.

**Non-Goals:** No new payment/access mutation, native-client redesign, arbitrary SQL/date ranges, provider call on read, fixture data, invented growth, mixed-currency totals, silent telemetry attribution or external MCP permission expansion.

## Decisions

1. Keep the existing `/statistics` reader/MCP/basic export contract intact. Add strict first-party section analytics composed into the read router, with section `home|overview|course|platform|funnel|money|sources|report|experiments`, existing period/platform allowlists and no browser-provided user/URL/SQL selector. Recheck live cookie/admin authority before and after cache IO, releasing SQL connections across that IO.
2. Reuse the existing daily snapshot implementation with server-controlled section namespaces and a shared compute mutex/healthy-worker refresh lease where needed. Separate R2 namespaces prevent one section replacing another. Do not eagerly load unopened sections, refresh every card, add cron, or reuse basic cache entries as expanded analytics. Keep bounded failure cooldown, size and deadline contracts. Default constructor behavior stays compatible with existing statistics consumers.
3. Use scalar/grouped/window/correlated SQL or proven bounded existing projections. Project counts and typed aggregate rows only; do not return learner identifiers, raw payloads, prompts, device tokens or private feedback. Dates stop at the captured generation time. Overall account identity is canonical-first with fallback only for genuinely unowned legacy positive Telegram rows. Distinct users and event/lesson/payment counts retain different names.
4. Home uses four real KPIs, an actual dated activity series, review tasks that open their actual current queue/filtered cohort, and existing user/message/limit/price operations. Cards/queues clearly share the original snapshot timestamp; action/profile/payment reads remain live. An expiring-Pro shortcut must use the same canonical predicate as its count rather than a loosely related user list. Quick actions never invent a target ID or bypass the original editor/passkey.
5. Overview combines users, activity, payers, status counts, course engagement, language/level distributions and the dated chart. Course covers mature retention, activation, Starter/foundation, measured session/lesson durations, QA/Voice and paid/free usage from their actual definitions. Funnel preserves tracked attempt IDs or explicitly labels independent events; do not compute ordered conversion from unrelated stage totals. Platform views retain real instrumented population/date scope and overlap; absent instrumentation is an honest unavailable state.
6. Finance separates exact currency totals from clearly labeled USD-equivalent/model-cost estimates. Unknown pricing is counted and excluded from priced sums. Renewal/first-payment classification uses canonical owner history; ARPU/ARPPU/check denominators are explicit. Sources use actual subscription-entry/traffic counts and nearest prior-entry attribution with its real observation window, not causal credit. AI model/tier and source rows have fixed bounds and safe text handling. Report exposes source/date/coverage/measurement notes and bounded first-party exports rather than demo/source-code prose.
7. V10 uses 4/2-column KPI grids, two-column chart/detail panels, real progress tracks, dense readable tables and existing seven subtabs/scope controls. Preserve compact Mac chrome, five mobile icons/More, accessible focus, reduced motion, safe areas and single contextual actions. Remove demo banners, fake percentages, hardcoded rows and implementation commentary. The advanced disclosure lazily requests experiments; it shares the same daily scope and private-state fencing. No unrelated navigation redesign.
8. New UI strings are authored together in canonical UZ/RU/TJ. Generated catalogs are rebuilt/checked. Dynamic values/names remain escaped; only fixed server enum values select known catalog labels. DOM/tab/filter changes ignore stale analytics responses and preserve private/no-store/offline/session-clearing boundaries.

## Risks / Trade-offs

- Wrong denominator/identity/source → audit current source and fixture differential tests before exposing each metric; retain explicit scope and unknown/null handling.
- Heavy historical reads → section-on-demand daily caches, SQL aggregates, bounded grouped output, statement/whole-load deadlines, no eager legacy overview.
- Missing/immature data → render null/unavailable/collecting distinctly from real zero; never substitute demo multipliers or a different metric under the same label.
- Native coverage and currency drift → preserve audited platform source/rolling windows and actual pricing snapshots; show estimates as estimates and unknown pricing counts.
- Cached authority/export leakage → live guards around cache IO, strict output allowlists, bounded files, no browser cache or expanded MCP projection.
- Dense mobile UI/regression → real ASGI/native-WebAuthn browser checks at 390/1440 in all locales, no overflow/console errors and cancellation/state regression.

## Migration Plan

No schema or rollout change is planned. Add read projections/cache namespaces first, verify source/count/privacy/performance invariants, then connect the two views and verify real responses. Commit/push verified increments on the owner's feature branch. Promote tested intended code through a clean worktree under current Git policy; preserve unrelated changes. Roll back new reads/views within the existing disabled PWA boundary without affecting legacy Admin or source records. CLI validation is planning evidence only.
