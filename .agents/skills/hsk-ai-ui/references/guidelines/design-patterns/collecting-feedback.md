> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-patterns/collecting-feedback.mdx`, Git blob `5e8c950b767db01e3aed7fe84d14ad0dc22bdd79`; 4 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# HSK AI feedback and problem reporting

Learners can provide feedback about supported learning experiences or report a technical problem through the **actual HSK AI channels**. A satisfaction question, product suggestion and technical bug report are different flows and must not be combined solely to imitate a widget pattern. This page documents **existing verified iPhone PWA code and target safety requirements** separately; it does not claim every flow is available on Android.

## Contextual lesson and experience feedback

The current iPhone PWA has server-prepared feedback for eligible lesson, foundation, practice and voice contexts, plus ordinary and release campaigns. The server determines question content, available answer choices and whether the learner can answer.

- Feedback concerns a **real identifiable activity** and only fields the current service supports.
- A guided response may collect **both** what was liked and disliked together. Do not replace it with a one-click vote or submit a separate unrelated answer for each selection.
- Some release campaigns may include a star rating/comment; these are different from per-lesson choices. Do not claim public ratings exist.
- The learner's account, lesson context, campaign identifier and response eligibility are server-authoritative.
- Do not interrupt active practice, an unfinished form, the red AI Voice Orb, login or external payment returns with an unexpected feedback sheet.
- Use clear categories and localized text in supported languages. A small, scannable group of choices is generally preferable, but **the server-provided choices are authoritative**; do not drop required categories to match a fixed design count.
- When a comment is required, explain **why** and validate it against the actual question; don't force unrelated fields purely for analytics.

## General suggestions

A product suggestion concerns the interface or learning experience rather than a single scored exercise. Offer only a real available support/feedback entry point; do not invent a universal toolbar, ticket system, admin identity or reply timeline.

Collect only fields relevant to the selected supported channel. Do not attach full URLs, private screen contents, learner identifiers or diagnostics without a legitimate need, backend handling and appropriate disclosure.

## Technical problem reporting

The iPhone PWA has a separate **technical problem report** supporting a description, a possible screenshot and a server submission.

- Distinguish a failed lesson save, network failure or broken feature from a satisfaction score.
- When capture is available, the present PWA tries an on-device screenshot and presents a preview with an attachment switch **ON by default**. The learner can turn it off before sending. **That is opt-out, not affirmative opt-in**; do not describe the existing behavior as consent by default.
- The screenshot may contain private information. The desired privacy rule is clear disclosure, preview, safe capture/redaction, explicit control and secure ownership verification. If the product chooses true opt-in, a separate implementation change must default the checkbox to OFF and require a positive user selection.
- Capture does not mean uploaded; only show “sent” after the real server response.
- Do not quietly attach a screenshot to ordinary lesson feedback.

## Submission, failure and dismissal

### Required future design behavior

1. A confirmed success message requires an actual server-accepted submission; network navigation or an optimistic UI is not proof.
2. Avoid duplicate submits while awaiting a response. On failures, preserve the unsent description and supported attachments and offer a clear retry.
3. Do not silently discard a typed draft on outside tap, Escape, system Back or a close icon. Preserve recoverable state or explicitly confirm abandonment, while retaining accessible focus restoration.
4. A pending submission must not be canceled in a way that makes its outcome silently ambiguous. Reconcile the server result before showing an error or inviting a duplicate.
5. Use a real HSK AI phone dialog/sheet layout and keyboard clearance. A source desktop popover or fixed 425 px width is **not required**.
6. Keep simple labels, sufficient iPhone/Android touch targets, screen-reader status announcements and text readable in both themes.
7. Do not disguise required errors or privacy disclosures in a two-line optional expansion.

### Observed implementation gaps (iPhone PWA only)

The following observations came from inspecting `app/static/course_v3_data/iphone-pwa-feedback.js` and `iphone-pwa-shake-report.js`; they are **not already implemented fixes**.

| Finding | What the current PWA code does | What should change in a separate production task |
| --- | --- | --- |
| Contextual survey dismissed by scrim | Outside tap calls `close()` and resets the `draft` object; Escape can also close. | Avoid loss of unfinished feedback or explicitly confirm discarding it. |
| Technical report dismissed by scrim | Close clears the report description and captured image; outside taps and Escape can trigger it. | Preserve or explicitly confirm clearing an unsent report. |
| Survey close while sending | The submit button becomes disabled, but the survey close handler does not fully block dismissal; its final response may be hidden. | Resolve the close/submit race and do not invite duplicate submission. |
| Technical report during send | The technical report closes only when not currently submitting. | Retain a clear pending/result state without duplicate sends. |
| Screenshot default | Available capture has its attachment switch checked by default, though the user can uncheck it. | Make consent behavior explicit and privacy-appropriate. |

## Restored professional source examples

> **Historical education-product diagrams only.** These examples preserve valuable interaction, composition and state patterns, not HSK AI's actual screens, roles, artwork, data or feature inventory. See the HSK AI-specific rules above before making a production design decision.

### Example 1: hero collecting feedback

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Original feedback-positive/negative illustration; not an HSK AI voting screen. Source asset: `./assets/collecting-feedback/hero-collecting-feedback.png`.

**Contextual sentiment:** a source-level thumbs-up/down interaction is not equivalent to HSK AI's current server-prepared lesson survey.

### Example 2: feedback trigger opinion

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Source in-content opinion feedback affordance. Source asset: `./assets/collecting-feedback/feedback-trigger-opinion.png`.

**Discoverability:** invite feedback near the content it evaluates, but only through a real supported HSK AI feedback campaign/route.

### Example 3: feedback trigger general

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Source general feedback entry point on a teacher dashboard, not an HSK AI admin feature. Source asset: `./assets/collecting-feedback/feedback-trigger-general.png`.

**General suggestions:** product feedback has a different intent from a reproducible technical error; don't invent a teacher navigation item.

### Example 4: feedback open widget

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Original compact feedback popover example. Source asset: `./assets/collecting-feedback/feedback-open-widget.png`.

**Form anatomy:** use readable choices, concise explanation, optional comment where configured and a safe submission/close behavior. A fixed desktop popover width is not mandated on phones.

### Acceptance and error cases

1. Show feedback choices and eligibility only when the existing backend actually provides them; preserve typed text and the user's selected response on transient failure.
2. Distinguish a successful server acknowledgment from a pending request, and prevent accidental duplicate sends.
3. Preserve the already-audited iPhone PWA gaps: backdrop dismissal currently clears unsent form content; survey close during send has race conditions; report screenshots default to **opt-out attachment** rather than explicit opt-in. These are **observed issues**, not fixed functionality.
4. If a future change makes attachments opt-in, test user privacy and do not silently attach a screenshot to an unrelated satisfaction question.
5. Keep real HSK AI localized buttons, focus return and touch sizes. Never overwrite a user's account or session to match the school-based source illustration.

## Restored professional feedback-pattern details

### Select a feedback type by the user's goal

- **Contextual sentiment** concerns a particular real lesson, exercise, AI response or supported feedback subject. **General feedback** covers the experience or feature suggestion. **Technical reporting** describes a reproducible failure with diagnostics only under the existing consent and privacy rules.
- Do not force a universal thumb-up/down widget on HSK AI. Its existing server-prepared lesson survey can collect **both positive and negative aspects** in one response; retain the real question list, eligibility and response contract.
- If a design adds selectable feedback reasons, make them user-language labels of **one to three words**; roughly **five choices plus “Other”** is a usable upper-bound heuristic, not a backend schema change. Offer distinct lists for positive and negative intent only when the actual flow uses separate intent states.

### Compose text and choose placement

- Write a prompt about what the learner has just done, not what a product team wants to measure. Never use another platform's classroom, video editor or paid tutor as a suggested HSK AI feature.
- Show feedback close to the context **without covering the required lesson action**. On mobile, choose the **professionally designed sheet/dialog** and keyboard/safe-area treatment appropriate for a real supported feedback channel; current functional submission/draft behavior is binding, but today's sheet visual design may be improved. Do not port a desktop source popover literally.
- Allow free-text when the active question requires or permits it; do not change optional comment rules or force an attachment. When a bug screenshot could reveal personal data, **explicit opt-in** is the desired target and the currently observed default-on behavior remains an unresolved app defect.

### Pending, confirmed and failed state

- Keep selected choices and text while the response is pending or a retryable error occurs. Disable only the particular duplicate-submit action, not the ability to copy or review an unsent draft.
- Treat a successful response as successful **only after the verified server acknowledgment**. Do not count a click as a submitted survey, and do not send one response twice after reconnect.
- Dismissal must not silently throw away unsent content. Where the current PWA does not meet this requirement, document it as a remediation task, **not** a tested current capability.
- For technical reports, use the real support endpoint and actual request ID/status where provided, not a simulated confirmation or a fake “support received” banner.

## Scope and verification

Server feedback eligibility, answers, ownership checks, release campaign rules and actual app behavior must not be changed during a **documentation-only** update. The Android reporting workflow was not independently confirmed in this audit; inspect its present screens before adopting parity claims or rewriting code.

The design document intentionally excludes unrelated school, teacher, mascot, source-product video-feedback and other-brand component examples. Any implementation requires a separate testable task.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: feedback-open-widget.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-patterns/collecting-feedback/feedback-open-widget.png)

- [feedback-open-widget.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-patterns/collecting-feedback/feedback-open-widget.png) — exact source blob `9b16a4037eba` (illustrated above)
- [feedback-trigger-general.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-patterns/collecting-feedback/feedback-trigger-general.png) — exact source blob `f7b51a63072b`
- [feedback-trigger-opinion.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-patterns/collecting-feedback/feedback-trigger-opinion.png) — exact source blob `d2c52712f4fe`
- [hero-collecting-feedback.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-patterns/collecting-feedback/hero-collecting-feedback.png) — exact source blob `305b46050e7c`
