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

### Requirement: Deliver existing learner notifications through an explicitly enabled PWA push channel
The PWA SHALL offer background push for existing account/service and course notification sources through a user-gesture permission and an owner-bound subscription. Push SHALL be additive to current Android/Telegram behavior, deduplicated per PWA device/event, and link back to the authenticated existing inbox/course. It SHALL NOT send private lesson, payment, or feedback content in the push payload.

#### Scenario: Enable PWA notifications
- **WHEN** an authenticated learner explicitly enables notifications from a supported installed PWA
- **THEN** the browser requests OS permission from that user gesture and registers the resulting subscription to the same canonical `users.id` and active PWA device
- **AND** permission is not requested automatically, in a Safari tab that cannot receive push, or when the feature is disabled

#### Scenario: Existing account or course event
- **WHEN** a new canonical account/service or course notification is recorded for a learner with an active PWA subscription
- **THEN** one visible, privacy-safe push is queued per active PWA device and event, with a safe PWA destination
- **AND** the existing Android/Telegram delivery, acknowledgement, fallback, daily study cap, and inbox record remain unchanged

#### Scenario: Revoke, expire, or switch account
- **WHEN** OS permission is revoked, the push endpoint expires, the PWA session is revoked, or the account changes
- **THEN** the endpoint becomes ineligible or revoked and cannot receive the next account's notices
- **AND** an uncertain provider attempt is not replayed as though delivery were known

### Requirement: Integrate Smart study push under existing consent and routing policy only
PWA Smart Reminder delivery SHALL use the existing canonical `users.id` preference, consent, job, selected-channel, one-account/local-day, capability, and attempt contracts in `docs/smart-reminders/SMART_REMINDER_MASTER_PLAN.md`. A general PWA push subscription SHALL NOT by itself grant Smart study consent; no second scheduler, reminder job, fallback, or account-level preference may be created.

#### Scenario: Eligible installed PWA destination
- **WHEN** an existing Smart job is eligible and the account's explicit Smart preference permits the PWA channel, the PWA is installed, OS push is allowed, and its owner-bound subscription is active
- **THEN** the existing selection and attempt flow may deliver that one server-owned job to the selected PWA destination
- **AND** a manual Telegram/Android channel lock, Smart OFF, unknown consent, invalid capability, stale session, or already attempted job prevents the PWA send

#### Scenario: Smart study is disabled or cannot be proven
- **WHEN** Smart study is OFF, PWA channel consent/capability is missing or stale, or an external delivery result is unknown
- **THEN** no PWA study reminder is sent and no other channel is silently selected or replayed

#### Scenario: Account/service notice is not a study reminder
- **WHEN** a subscription, payment, expiry, or limit notice is sent through PWA push
- **THEN** it remains outside the Smart Reminder daily study cap and does not create Smart consent or a Smart job

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
