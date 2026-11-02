# iPhone PWA — messages, Smart Reminder handoff and feedback

## ADDED Requirements

### Requirement: Preserve the existing categories and authorization of HSK AI notifications
The standalone learner PWA SHALL preserve existing **distinct** message classes and canonical ownership, rather than silently dropping them because it has no Telegram `initData`: (a) account/transactional notices such as subscription, payment, expiry and limits; (b) existing ranking, weekly, motivation and course inbox information; (c) study reminders, which belong to the separate Smart Reminder policy; and (d) applicable user feedback/release-feedback requests. The browser MAY display authenticated, eligible current-account messages from current services, with a narrowly scoped adapter only where existing APIs are Telegram-only. It SHALL NOT invent receipt/delivery status, duplicate an already-sent external notice or assume every notification class is already stored in `CourseUserNotification`.

#### Scenario: Browser-only user without Telegram
- **WHEN** a verified PWA account has `telegram_id=NULL` and an important subscription or limit status exists
- **THEN** the app displays the server-confirmed account status and any supported authenticated in-app notice when opened
- **AND** it does not invent a Telegram destination or treat an opened inbox item as a push-delivery receipt

#### Scenario: Existing account service notice
- **WHEN** an existing `NotificationDeliveryService` account notice is delivered through permitted Android/Telegram fallback
- **THEN** the PWA addition does not change its existing acknowledgement, escalation, deduplication, payment ownership or eligibility
- **AND** such service notices are NOT subjected to the Smart study reminder 1/day cap

#### Scenario: Ranking or course notification
- **WHEN** a course/inbox item is read in the PWA
- **THEN** the action and content are derived from the canonical account and authorized course target, preserve UZ/RU/TJ rendering, and do not mutate transport delivery or grant access

### Requirement: Be ready for Smart Reminder V2 without prematurely enabling Web Push
The PWA SHALL be designed as a **future channel adapter** of `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md` D01/D03/D05/D06/D07/D10/D14 and the platform-neutral canonical `users.id` Smart preference/job/target contracts. It SHALL not introduce its own scheduler, daily reminder job, account-level opt-in, duplicate fallback or fake notification capability. Initial PWA release requires no push service worker, OS permission or subscription; those are necessary future V2 integration work with a separate tested browser push adapter.

#### Scenario: First PWA launch before Smart V2
- **WHEN** an installed or Safari PWA has no approved Web Push transport
- **THEN** it reports its PWA channel as unsupported/not-registered rather than available
- **AND** it does not request permission, enable an existing OFF channel, or dispatch a study reminder

#### Scenario: Future Smart Reminder integration
- **WHEN** the approved V2 Web Push integration is implemented later
- **THEN** only a real supported installed PWA with user-gesture OS permission, owner-bound Push API subscription, valid consent and verified device capability can become an eligible channel under the **existing** Smart Reminder selection engine
- **AND** only the server-owned logical study job with its one-account/local-day bound, allowed chosen channel, acknowledgement and conservative fallback authorizes delivery; no duplicate PWA scheduler or account-wide preference table appears

#### Scenario: Opt-out and identity change
- **WHEN** a user disables Smart reminders, loses OS permission, signs out, removes an installation or switches accounts
- **THEN** future PWA push subscription/capability is invalidated or marked ineligible without reviving OFF, changing other channel consent or automatically choosing another provider under an unknown outcome

### Requirement: Compact centered in-app feedback from the existing bot flows
The PWA SHALL support the existing eligible ordinary bot feedback questions and release-feedback rating experience in a **small, dismissible, centrally aligned dialog** that does not replace the underlying course page. It SHALL reuse canonical `BotFeedback`/`ReleaseFeedback` owner, eligibility, campaign, response, reward and deduplication rules. The existing Telegram chat interaction remains unchanged. The PWA SHALL NOT show a modal solely because a Telegram chat message was sent, request an unsolicited campaign, invent another bonus, or surface an unrelated user's feedback.

#### Scenario: Eligible ordinary feedback prompt
- **WHEN** the authenticated user's canonical feedback state marks a prompt eligible for PWA display
- **THEN** a compact centered dialog shows the equivalent positive/negative choice and supports needed subsequent details
- **AND** dismissing it preserves the course and respects existing prompt/attempt/suppression rules rather than forcing an answer

#### Scenario: Eligible release-feedback campaign
- **WHEN** the user's active eligible release-feedback campaign requires a 1–5 rating or optional comment
- **THEN** the corresponding centered dialog collects the supported response and returns to the previous screen
- **AND** discount, reward, paid/free status and review completion are confirmed only by existing server-side rules

#### Scenario: Same prompt in Telegram and PWA
- **WHEN** a linked learner views or answers feedback on either platform
- **THEN** both clients address the same canonical feedback record and campaign, and duplicate replies/bonus grants are prevented by the server

### Requirement: Figma-first for genuinely new PWA UI
Before implementing a **new** learner screen or component, an editable Figma mockup/component SHALL be created or reused, linked from the single `docs/IPHONE_PWA_CONTEXT.md` handoff and reviewed against existing `app/static/course_v3_data/design-tokens.css`, `hsk-ai-ui` skill and live Mini App rendering. Existing unchanged Mini App screens SHALL be reused without a redundant full redesign. Figma approval is a design gate, not proof of an implemented UI.

#### Scenario: Implement a notification screen or feedback dialog
- **WHEN** work begins on a net-new PWA notification inbox, settings section or feedback overlay
- **THEN** its Figma file and exact reusable component/node mapping are inspected first
- **AND** UI behavior, accessibility, state and UZ/RU/TJ canonical copy are reconciled before applying code changes
