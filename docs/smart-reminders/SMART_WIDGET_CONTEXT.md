# Shared passive widget context, version 1

Canonical scope/progress: [Master Plan](SMART_REMINDER_MASTER_PLAN.md), D15 and
latest checkpoint. This document defines the wire and cache contract, not a
second progress ledger. The pure implementation is
`app/services/smart_widget_context.py`; authenticated source reads are in
`smart_widget_context_service.py`. Android rendering/store integration is P4
tasks 5.5–5.6. iOS and paired macOS/Windows hosts remain later adapters.

## Authenticated optional map field

Existing Android bearer-authenticated `GET /api/v3/android/course/map` accepts
the optional pair `widget_context_version=1` and
`widget_context_epoch=<canonical UUID for the current local link>`.
Existing `tz` remains the bounded coarse course offset; it does not choose an
IANA zone. No pair means the original map contract and no new Smart reads.
The response adds `widget_context` only for an explicit supported request.
Existing map/goal/display-XP/notification fields remain unchanged.

The opt-in request allows only these three query keys. Missing, unsupported,
malformed or duplicate protocol fields, duplicate `tz`/Authorization and mixed
Telegram proof return `422 widget_context_request_invalid`. A cookie or query
owner is never authentication. Real native bearer auth is required; the first
bridge requires an Android device. macOS/Windows routes and consent are not
expanded. Future authenticated adapters reuse the pure contract with their
own verified platform bridge, without an independent habit model.

Fresh canonical ownership, session/device expiry/revocation, account state and
submitted deletion are checked using P1 before normal map work and again for
projection. Existing P1 `smart_*` refusal codes/statuses remain applicable.
A changed course returns `409 course_context_changed`; a proof expiring during
validation returns `401 widget_auth_expired`. Responses are `Cache-Control:
no-store`; existing normal map initialization/writes are unchanged. The added
projection itself performs no writes, autoflush, commit, migration, event,
consent import, study reservation or provider call.

## Envelope and minimal cache allowlist

`WidgetContext` is the strict, immutable schema. These are the complete allowed
fields; adapters do not copy the entire course map into widget storage.

| Fields | Meaning |
|---|---|
| `version=1`, `policy_version=smart-widget-context-v1` | Explicit contract/semantic version. Unknown versions require neutral/compatible rendering. |
| `binding`, `request_epoch` | Opaque SHA-256 correlation of the verified canonical owner/device/session and the captured per-link UUID. Neither authorizes an operation. No raw owner/session/device ID is stored. |
| `revision`, `generated_at`, `valid_until` | Current preference revision and aware UTC validity window; equality with expiry is expired. |
| `level`, `track`, `local_day`, `timezone_name` | Canonical content level/track and authoritative IANA day/zone. Missing zone gives NULL day/zone and neutral daily state; no offset-to-zone guess. |
| `completed_parts`, `total_parts` | Fresh matching-course progress; NULL when inconsistent. |
| `verified_today_xp`, `goal_xp`, `goal_state`, `plan_completed` | Corroborated learning XP, existing goal and stored-plan result. Unknown/mismatched day cannot assert completion. `not_proven` is not proof of no study; verified XP can undercount legacy activity. |
| `time_local`, `time_source`, `time_reason`, `calibration_version` | Shared policy time and source (`manual`, `saved`, `habit`, `unknown`), with no new confidence default. A missing usable minute has unknown source. |
| `phase`, `reason`, `action`, `lesson_order`, `coverage_limits` | Semantic presentation and a normal navigation suggestion. No layout/art/OS/size IDs or private lesson content. |
| `dispatch_allowed=false`, `action_requires_authorization=true` | Fixed real JSON booleans, including on retries; JSON 0/1 are rejected. No notification or access grant. |

No credentials, names, raw learning history, message bodies or private lesson
data enter this envelope. Store only this allowlist in the platform's protected
minimal widget bridge. The existing local epoch remains the installation's
response fence, not an account identifier or a server credential.

The deadline is the minimum of the verified bearer expiry, actual next IANA
midnight and the next known personal-time/quiet/pause boundary. It never extends
the proof, adds a product TTL or promises an OS refresh at that instant. DST
days use real midnight boundaries, including 23/25/23.5-hour days. Ambiguous or
nonexistent personal clocks remain neutral instead of silently shifting time.
If time advances while User is locked/validated, generated time is sampled
again. Offline adapters become neutral at expiry even if the OS delays refresh.

## Semantics and reason codes

| Phase / reasons | Behavior |
|---|---|
| `before_study` / `before_personal_time` | A real manual/saved/explicitly calibrated habit clock is still ahead. |
| `study_time_reached` / `personal_time_reached` | That personal clock has been reached. This is not overdue, failure or a critical mood. No global 22:00 escalation. |
| `completed` / `goal_completed`, `plan_completed`, `course_completed` | Calm completion from verified current-course facts. Reward XP, app/widget opens and shadow job completion do not count. |
| `paused` / `personal_pause`; `quiet` / `personal_quiet` | Restrained view; no notification fallback. Incomplete/all-day quiet settings and DST-ambiguous/nonexistent quiet boundaries also restrain. |
| `neutral` / `study_off`, `personal_time_unknown`, `timezone_unknown`, `course_day_mismatch`, `target_inaccessible`, `local_time_nonexistent`, `local_time_ambiguous` | Keep permitted ordinary progress without inventing urgency, habit, comeback or inactivity. Unknown daily context exposes no daily completion. |
| `neutral` / `foundation_required` | Suggest only the normal foundation route, with no lesson target. |
| `unavailable` / `course_context_changed` | No progress claim or continuation target from inconsistent course state. |

Priority: consistent course/day, required foundation, proven completion, global
OFF, pause, quiet, current target access, then personal time. `course` opens the
normal authenticated course shell; `continue` suggests the next allowed order;
`foundation` opens normal foundation; `none` has no target. All destinations
revalidate live foundation, order, course track and entitlements. A cached
action is not a quota reservation or lesson-access ticket.

Notification channel OFF or OS denial does not blank permitted passive progress
or create consent. Global OFF restrains unfinished presentation; a completed
day can still be calmly completed while OFF. Current runtime habit confidence
remains unconfigured: genuine saved/manual time works, and QA habit fixtures
are not a deployed confidence threshold. No per-refresh LLM call is made.

## Response acceptance and lifecycle

`widget_cache_reason` is a reference contract validator, not an installed
adapter or snapshot signature. `widget_context_current` only permits passive
presentation under its current bindings. Rejections are `widget_context_invalid`,
`widget_session_changed`, `widget_context_changed`, `widget_context_replayed`,
`widget_context_future` and `widget_context_expired`; all require a neutral or
cleared view and normal authenticated refresh.

1. Capture the current protected native-session generation and local link epoch
   when issuing the authenticated map request. Never put bearer proof in a URL
   or widget cache.
2. Before accepting even a first response, verify that the app still has that
   same session/generation/epoch. A response echo alone cannot establish this.
   Establish opaque binding and canonical course/day/zone only from that
   confirmed-current authenticated response/account bridge. Never establish a
   current owner by copying an arbitrary cached envelope's own fields.
3. Compare subsequent envelopes against the bridge's current expected binding,
   epoch, course/day/zone and known minimum revision/latest accepted generation.
   Reject future, expired, unsupported, wrong-context, lower-revision or older
   generated responses. Known track/zone/clock changes neutralize old snapshots
   pending refresh; an old response cannot choose a previous course again.
4. Logout, relink, session loss/revocation and deletion clear visible/cache
   state and rotate the local epoch; discard every pending old-epoch response.
   Do not restore an account from cached progress or a widget tap.

An offline adapter cannot discover a remote revocation or OFF immediately.
Finite presentation expiry, local generation fences, known revision changes
and mandatory live action checks bound that limitation. No instant global
cache revocation or exact-time refresh is claimed.

Shared fixture source: `tests/fixtures/smart_widget_context_v1.json` (31 semantic
cases). Reference tests also cover envelope/session/replay failures, source
ownership/zero writes and the actual authenticated Android map. Later render
adapters must consume these semantics and add their real storage/host/privacy/
launcher lifecycle acceptance. Rollback omits the optional field or uses a
neutral renderer, preserving P1 OFF/revision/epoch guards and shadow ownership.
