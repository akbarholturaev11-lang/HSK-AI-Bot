# Smart Reminder Orchestration — Spec Delta

## Purpose

Coordinate study reminder decisions and delivery once per canonical learner account across permitted channels, with adaptive timing and truthful outcomes. This proposed contract replaces independent study senders only for safely migrated cohorts.

## ADDED Requirements

### Requirement: Account-wide study budget
The system SHALL reserve at most one logical study reminder intent per canonical account and frozen local calendar day across Telegram and all Android installations. A fallback attempt MUST remain part of that same intent. Concurrent workers and repeated triggers MUST NOT create a second authorized study intent for that day (D03/D06).

#### Scenario: Telegram and two phones become due together
- **WHEN** Telegram and two Android installations for one account are due and two schedulers claim concurrently
- **THEN** only one account/day study intent is authorized, with one selected destination and no all-device broadcast

#### Scenario: Repeated FCM and periodic checks
- **WHEN** FCM and the periodic Android check both wake for one selected job
- **THEN** neither creates a separate reminder and repeated claims cannot authorize a second post

#### Scenario: Change of timezone near midnight
- **WHEN** a user travels or changes device timezone while an account/day study intent is reserved
- **THEN** the original owner, IANA zone and local day remain attributable; any ambiguous new day is suppressed until safe rather than allowing a duplicate intent

### Requirement: Fresh eligibility at dispatch
The system MUST recheck account status, study consent, selected device/channel capability, current lesson, daily goal, quiet/pause state, cap and expiry immediately before dispatch. An incomplete or inaccessible target MUST NOT produce a misleading notification or bypass course/Pro entitlements (D01/D03/D04).

#### Scenario: Goal completed after scheduling
- **WHEN** the learner completes today's goal on another client before dispatch
- **THEN** the pending study intent is suppressed and no replacement study intent is sent that day

#### Scenario: Lesson or course changed
- **WHEN** the learner switches HSK track, finishes the proposed lesson or loses access before dispatch
- **THEN** the stale lesson deep link is not delivered; any surviving target is independently validated under current access rules

#### Scenario: Opt-out while provider attempt waits
- **WHEN** explicit global OFF or channel OFF commits before the authorized send boundary
- **THEN** the new attempt is denied and queued grants are invalidated

#### Scenario: Auth or ownership no longer valid
- **WHEN** the account is blocked, pending deletion, logged out or the selected device is revoked/relinked
- **THEN** no new study attempt or client post for the old account is authorized

### Requirement: Adaptive time and cadence
The policy SHALL use verified study behavior to adapt reminder time and frequency, with useful rules immediately available to sparse-history users. It MUST retain a genuine legacy time until history is reliable, honor deliberate manual locks, user quiet/pause controls and OS limits, and never impose a global night blackout (D02/D03/D04).

#### Scenario: Cold-start learner
- **WHEN** a historically permitted learner has insufficient reliable study history and a saved reminder time
- **THEN** that time remains the scheduling source without a new activation prompt or fabricated manual lock

#### Scenario: Late-night study pattern
- **WHEN** reliable individual study behavior favors a night hour and no explicit personal or OS restriction blocks it
- **THEN** the policy may schedule that hour while still enforcing the one-per-day account limit

#### Scenario: Repeated nonresponse and later learning
- **WHEN** several eligible reminders do not lead to server-confirmed learning
- **THEN** later reminder intervals lengthen; when verified useful learning returns, cadence may increase only within the daily cap

#### Scenario: Open without study
- **WHEN** a user opens a notification or app but records no verified learning
- **THEN** that open alone is neither a completed goal nor conclusive evidence that the reminder improved learning

### Requirement: Personal reactivation
Reactivation SHALL reflect the account's normal study rhythm and offer a real accessible lightweight learning action. Without useful study return, successive reactivation attempts MUST become less frequent and ultimately stop; no universal 3/7/14-day sequence or invented lesson duration is allowed (D08).

#### Scenario: Different normal rhythms
- **WHEN** a daily learner and a twice-weekly learner both have a three-day gap
- **THEN** the policy may classify their inactivity differently using their own verified histories rather than the same fixed delay

#### Scenario: Repeated unsuccessful reactivation
- **WHEN** prior reactivation messages have no confirmed study return under the approved observation policy
- **THEN** the next eligible intervals widen and the series ultimately stops; any new study activity is assessed for safe restart

### Requirement: One eligible destination
For each study intent, the system SHALL select one currently consented and reachable channel and one eligible device where applicable. Automatic selection MUST use verified platform study activity and delivery reliability; an intentional manual channel lock takes priority only while permitted. Unsupported channels MUST NOT be selected (D06/D10).

#### Scenario: More learning on a permitted phone
- **WHEN** an account has permitted Telegram and two Android devices, and verified study/reachability evidence favors one phone
- **THEN** only that eligible phone receives authority for the intent, without parallel Telegram or second-phone fanout

#### Scenario: Preferred channel unavailable
- **WHEN** a manually locked channel is blocked, permission-denied or unsupported
- **THEN** the policy suppresses the intent rather than silently overriding the lock with an initial send elsewhere

#### Scenario: No trustworthy destination
- **WHEN** all endpoints are OFF, revoked, blocked, permission-denied or otherwise uncertain
- **THEN** the intent is suppressed with a reason and no provider attempt

### Requirement: Truthful delivery states and safe alternate
The system MUST distinguish a reserved intent, provider acceptance, client post invocation, independently verified display where available, and learning outcome. A second channel MAY be attempted only after definitive first-attempt failure or authenticated credible non-display, within the same unexpired intent and after fresh policy checks. Timeout, no acknowledgement and unknown result MUST NOT authorize fallback (D07).

#### Scenario: Provider definitively rejects before display
- **WHEN** the first provider definitively rejects a send and another channel remains permitted
- **THEN** a controlled alternate may be attempted on the same job after rechecking consent, goal, cap, endpoint and expiry

#### Scenario: FCM accepted but no device receipt
- **WHEN** FCM accepts a data hint and the device provides no trustworthy display result before timeout
- **THEN** the outcome remains unconfirmed or unknown and no Telegram or second-device study fallback occurs

#### Scenario: Notification post method succeeds
- **WHEN** the Android notification API returns after a local post call without independent OS-display proof
- **THEN** the result is recorded as client-posted but unverified, never asserted as shown or read

#### Scenario: Late original hint after alternate
- **WHEN** a definitively failed original attempt's delayed hint arrives after an authorized alternate claim
- **THEN** the original client cannot obtain valid posting authority and the same job does not yield two authorized displays

#### Scenario: Worker crash after external provider call
- **WHEN** a provider accepts a send but the worker dies before a confirming database update
- **THEN** the outcome is treated as ambiguous; replay does not blindly send another channel or new daily intent

### Requirement: Robust due-window processing
Due study intents SHALL be processed through durable account-level ownership so scheduler overlap, restarts or unrelated task failures cannot create duplicate authorization. Missed ticks MUST result in a still-valid due-window attempt or an explicit expired/suppressed result, never a blind late send (D03/D04/D07).

#### Scenario: Two server replicas
- **WHEN** replicas process the same due intent concurrently or one resumes after a lease expires
- **THEN** only the current owner can authorize an attempt; stale ownership cannot dispatch

#### Scenario: Earlier admin poll fails or stalls
- **WHEN** an unrelated admin poll fails or delays a scheduler tick
- **THEN** the study queue preserves the intent for bounded independent processing and expires it if its valid window closes

### Requirement: Category coordination without policy leakage
Study, ranking and weekly progress messages SHALL keep distinct purposes but share account-level collision control. Ranking MAY be suppressed or deferred when less useful; a valuable weekly report MUST NOT be silently discarded. The one-per-day study cap MUST NOT be applied to transactional payment, subscription or account notices, whose existing delivery escalation remains unchanged (D05/D07).

#### Scenario: Three learning messages collide
- **WHEN** a study intent, ranking notice and weekly summary are due near each other
- **THEN** account-level priority prevents nuisance overlap, records each suppression/defer reason, and preserves the useful weekly report for a valid later window where possible

#### Scenario: Payment notice due with study reminder
- **WHEN** a transaction-bound account notice is due near a study reminder
- **THEN** its current independent access and Android-to-Telegram escalation contract remains in effect; the study budget does not consume or replace it

### Requirement: V1 channels and extensible core
V1 SHALL support Telegram bot delivery for the Mini App learner and compatible Android study notifications through the same account policy and job identity. Future learner iPhone PWA and macOS/Windows adapters MUST be addable without changing the canonical account, consent, local-day or deduplication semantics; unsupported V2 endpoints MUST remain inactive (D10).

#### Scenario: Telegram-only learner
- **WHEN** an eligible learner has a real reachable Telegram bot channel and no Android installation
- **THEN** one safe study job can target Telegram and its action opens an existing authorized learning path

#### Scenario: Native learner without Telegram
- **WHEN** an eligible Android account has no real linked Telegram ID
- **THEN** selection never invents Telegram transport or fallback

#### Scenario: V2 not installed
- **WHEN** a learner PWA or Desktop channel has no implemented and permission-verified adapter
- **THEN** it is not advertised as a deliverable V1 endpoint and does not block an otherwise valid Telegram/Android release

### Requirement: Safe localized content and experiment controls
Study content and actions SHALL use canonical UZ/RU/TJ text, validated parameters and existing lesson/access routes. Experiment control accounts MUST receive no treatment study reminder, and the existing D1 recovery holdout MUST retain its assignment and suppression semantics (D01/D10).

#### Scenario: Language changes after inbox storage
- **WHEN** a learner switches UZ/RU/TJ after an authorized reminder is stored
- **THEN** the feed uses source template data to render the requested language where supported without changing answer, grading or entitlement data

#### Scenario: Restricted lesson target
- **WHEN** a candidate points to an unavailable, locked or stale Pro lesson
- **THEN** the notification is suppressed or retargeted only after normal access validation; the CTA never bypasses paywall or Play purchase rules

#### Scenario: D1 holdout member
- **WHEN** an account belongs to the active existing D1 recovery control window
- **THEN** migration and new study routing preserve its no-treatment delivery behavior and do not reassign by device or Telegram transport
### Requirement: Native issuance and outcome integrity
Android posting authority SHALL bind a pre-reserved selected job, canonical owner/device/session, local account epoch, current preference/capability/cohort fences and finite server validity. Issuance SHALL commit before authority leaves the server. Client capability alone MUST NOT establish reviewed cohort admission or authorize dispatch.

#### Scenario: Claim response is lost
- **WHEN** the selected device loses or repeats a response after grant issuance
- **THEN** the retained issuance prevents another posting grant, even after expiry; no second device/channel or blind retry follows from uncertainty

#### Scenario: Device inventory changes after fencing review
- **WHEN** the reviewed account gains an installation/session or its relevant device/version/capability evidence changes
- **THEN** prior admission fails its inventory binding and cannot authorize a fresh grant

#### Scenario: Historical receipt arrives after OFF
- **WHEN** the original valid native session reports an already-issued outcome after OFF/expiry/dispatcher disable
- **THEN** the result may be recorded as history without renewing authority; revoked, blocked and deletion contexts remain refused

#### Scenario: Receipt conflicts with its first outcome
- **WHEN** a repeated callback changes the immutable receipt ID or outcome, or asserts shown/read/learning
- **THEN** the conflict or unsupported assertion is refused; an exact receipt retry acknowledges once and creates no new attempt
