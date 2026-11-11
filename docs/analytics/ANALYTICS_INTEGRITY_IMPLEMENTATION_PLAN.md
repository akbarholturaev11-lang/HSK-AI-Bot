# HSK AI — Analytics Integrity: shared context

> **This is the single shared context file for this work.** It is used by Codex, Claude and cloud agents alike.
> - Read it at session start. At session end, update "Current state", the audit table and the session log.
> - Do not create any other progress, context or handoff file for this work.
> - The checklist lives only in [`openspec/changes/hsk-ai-analytics-integrity/tasks.md`](../../openspec/changes/hsk-ai-analytics-integrity/tasks.md). Requirements live in its `specs/`, technical decisions in its `design.md`.
> - The permanent per-feature rule lives in root `AGENTS.md` ("Permanent analytics integrity and feature coverage").

## Goal

Connect the existing analytics of Android (Play/Direct), the Telegram Mini App and the iPhone PWA to the matching Admin PWA Analytics V10 sections (Overview, Course, Platforms, Funnel, Finance, Sources, Report).
- The connection must be complete and accurate, and proven by tests.
- Each platform must be viewable separately. Overall must count each canonical account once.
- Future features must not fall outside analytics: the `AGENTS.md` rule, the coverage registry and CI enforce this, and a justified `not_applicable` is allowed.

## Constraints

- Keep the existing V10 architecture. Do not build a new analytics system or duplicate working parts.
- No PostHog, no new Redis use and no other infrastructure without evidence of need. No schema change unless a reviewed task proves it necessary.
- Do not label anything a defect until real code confirms it. Unproven items stay `to_verify`.
- Do not change payment, Pro entitlement, access, grading, auth or privacy behavior. Telemetry must never block a user flow.
- A stored event or a passing unit test is not integration evidence. Only a chain test (event → API → PostgreSQL → aggregation → Admin PWA UI) is.

## Where things are

| Item | Location | Status |
|---|---|---|
| OpenSpec change | `openspec/changes/hsk-ai-analytics-integrity/` | Planned; passes `openspec validate --strict` |
| Checklist | `.../tasks.md` | Only checklist; nothing checked |
| Coverage registry | `docs/analytics/FEATURE_ANALYTICS_COVERAGE.json` | Not created (task 2.1) |
| CI guard | `.github/workflows/analytics-integrity.yml` | Not created (task 2.3) |
| Agent rule | `AGENTS.md` | Active since `b5c653ff`; enforcement status still "planned" |
| Admin readers | `app/admin_api/pwa_analytics*.py`, `pwa_metrics.py` | Unchanged |

## Current state — 2026-11-09

- Planning only. No runtime code has changed.
- The OpenSpec change was created with the real CLI (1.15.0) on branch `planning/analytics-integrity-openspec-20261109`, from `main` `8ff505b3`. It was simplified on owner request and is proposed as a PR, not yet merged.
- Verified code facts that drive the work are listed in `design.md` → Context:
  - PWA Pro events are written but read by no Admin reader;
  - the `iphone_pwa` filter returns `not_instrumented`;
  - non-overall filters return `attribution_not_audited` for Course, Funnel, Finance and Sources;
  - retention counts only `miniapp_opened`.
- **Next step:** task 1.1, the audit, which fills the table below. Then task 1.2, the regression fixture, before anything else.

## Platform scope

| Platform | Admin filter | Role in this work |
|---|---|---|
| Android Play + Direct | `android` | Target. Play/Direct split only if the channel is already recorded |
| Telegram Mini App | `telegram` | Target |
| iPhone PWA | `iphone_pwa` | Target |
| macOS / Windows | `macos`, `windows` | Keep existing metrics; registry status only |

## Audit table (task 1.1 fills this; `verified` rows need code and test citations)

| Flow / metric | Platform | Writer | Table | Platform field | Admin reader → section | Status |
|---|---|---|---|---|---|---|
| _not started_ | | | | | | |

## Decisions log

- 2026-11-09 — Single context file is this document. OpenSpec `tasks.md` is the only checklist.
- 2026-11-09 — Registry format is JSON, not YAML, because PyYAML is not a project dependency.
- 2026-11-09 — Removed from scope on owner request: client telemetry retry, intake counters, campaign attribution, error/performance analytics, D30, PR template.
- 2026-11-09 — PWA foreground proof: reuse an existing authenticated PWA record if one exists. Only otherwise add a minimal `pwa_active_day` event (design D3).

## Session log (newest first, one or two lines each)

- 2026-11-09 — Created and validated the OpenSpec change, added the owner's platform requirements, simplified the plan to 6 task groups, and turned this file into the shared context.

## History

The original long plan (phases 0–5, OpenSpec authoring handoff, per-feature contract) is preserved in git at `8ff505b3`. Its content now lives in the OpenSpec change and in `AGENTS.md`.

## Analytics → Monitoring → joint integration order

- **First:** deliver the Analytics Impact rule, coverage registry and scoped CI guard; continue metric repair in bounded packages. This prerequisite does **not** require finishing every Analytics report.
- **Then:** Monitoring reuses verified canonical user/platform/feature identifiers and compatible coverage/CI conventions. Keep business/KPI events separate from privacy-safe diagnostic incidents; no duplicate pipelines.
- **Finally:** one joint integration audit (not a third rebuild) checks both Impact/CI obligations, end-to-end Admin Analytics/Inbox coverage, dedup/privacy, nonblocking flows and affected regressions. Recheck the latest `main` and integrate tested changes sequentially.
