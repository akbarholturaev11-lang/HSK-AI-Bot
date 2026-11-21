> **HSK AI professional design guideline — portable review copy.** Current implementation is not implied. Source `__docs__/design-components/banners.mdx` (Git blob `7eb978d126911a64b013c178f4db66d0169fc3cc`); 4 historic figure references, 17 MDX demo blocks. Approved neutral example PNGs are linked below where available; excluded foreign screens and vendor runtime code were not transferred. The original prose remains an internal source-derived draft. Full professional prose is retained as an internal source-derived draft.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Banners. Source asset: `./assets/banners/banners.png`.

# Banners

> **HSK AI scope:** These original examples and interactive demonstrations describe professional alert hierarchy, severity, layout, iconography and dismissal—not HSK AI's finished branded UI. Use HSK AI's approved semantic colors, accessible icons, mobile spacing and verified account/lesson states. Source screenshots must not be copied into the HSK AI interface. **All sample text and button callbacks on this page are illustrative, not real server actions.** The links now point to actual related documentation rather than dead demo placeholders.

*Component role: Persistent/Global alerts*

A highly visible, non-modal container used to communicate important, global system status changes, successful operations, or errors. Banners remain persistent at the top of the viewport or relevant area until dismissed by the user or the issue is resolved.

## Recommended: When to use

The choice to use a banner is determined by the need for persistent, high-priority, and global system communication.

| Use when | Example use |
| --- | --- |
| High-priority feedback signals a significant change affecting the user's entire session or future state | Warning: Your verified HSK AI Pro access expires on the displayed account date, if renewal is available. |
| The message must stay visible until the user acknowledges it or the system resolves it | Error/offline status: "The lesson result could not be saved. Check your connection and retry." |
| Confirming a complex or high-stakes action that is difficult to reverse | Success confirmation: The verified purchase was completed and the corresponding HSK AI account access is active. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| Showing transient feedback | Toast | Do not use for low-urgency, self-contained, or temporary confirmations that do not require acknowledgment (e.g., "Preference saved"). Banners are too disruptive for simple confirmation. |
| Blocking the interface for a critical issue | Modal or full screen error page | The Banner is non-modal and allows the user to click around the background. A critical error requires blocking the entire interface. |
| Requiring a complex user decision | Modal | Do not use when the message requires the user to make an immediate, high-stakes choice or irreversible commitment. Banners lack the necessary context and visual gravity for complex decisions. |
| Displaying non-critical promotions | Contextual card or feature slot | Do not use for non-critical promotional or marketing content. Banners are reserved for system alerts and status changes, not upsells or temporary campaigns. |
| Highlighting a field-specific error | Inline form validation | Do not use for validation failures related to a specific input field (e.g., a required account field is empty). Banners are global, not local. |

## Variants

### Critical error/blocker

Do use when signaling a severe, system-wide failure, data corruption, or an issue that immediately blocks the user from completing a primary task, ensuring that the error message is not dismissible until the problem is resolved or the page state changes.

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: banner critical.

### Warning/action required

Do use when signaling a non-blocking but significant future risk or communicating a mandatory action that must be completed to prevent a problem, ensuring the user is aware of the potential negative consequence if they do not act. The banner must not be dismissible until the user has resolved the underlying issue.

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: banner warning: Plan access will end on {Renewal/Expiry date}. Renew now to keep features..

### Success confirmation

Do use when signaling the successful completion of a complex or high-stakes transactional action, especially if that action involves multiple steps or is difficult to reverse, ensuring the copy is specific, data-driven, and includes direct links or identifiers to the resulting content for immediate verification.

> **Illustrative demo:** Success banner with a clear success/check-circle icon (source example uses the Phosphor `checkCircleBold` glyph), verified outcome copy, related result/detail links where real, and an optional dismissal X. Its linked table/report titles and saved-state example are fictional and **not proof of HSK AI data or success**. Prefer a verified HSK semantic success role, not the ordinary brand-action color.

### Informational/feature

Do use when communicating temporary policies or essential guidelines that require a one-time user acknowledgement to dismiss the visual notice or when announcing new tools or key features to drive awareness.

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: banner info: Avoid sharing private information in learning conversations. Review the current HSK AI privacy notice..

## States

### Dismissal for informational and success banners

Do include the 'X' for a banner that is informational, feature-related, or confirms a successful transaction, allowing the user to clear visual clutter immediately.

> **Recommended demo:** include an X on success and info banners so users can clear them.. Example UI: banner success; banner info: AI answers can contain mistakes.

### No dismissal for unresolved state

Don't include the 'X' if the message communicates a state that the user cannot resolve on their own, or if the user must be continuously aware of the message to prevent an error or data loss.

> **Avoid demo:** include an X on warning or critical banners the user still needs to resolve.. Example UI: banner warning: Plan access will end on {Renewal/Expiry date}. Renew now to keep features.; banner critical: Your message was not delivered. Please try again..

## Iconography

The banner must include the system-defined type icon. The icon is the most immediate signal, helping users who may have color vision deficiencies or who are scanning the page quickly.

Do not use custom, context-specific icons (a "calendar" for maintenance) in the primary position, as this dilutes the meaning of the core status types.

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: source BannerIconography illustration.

## Actions

### Action type and singular focus

There are two action types: Button and Link. Use a Link when the action is primarily to navigate to a detailed page or section. Use a Button when the action is functional or mandatory and completes a process. Also, maintain singular focus. Banners should contain only one primary action to maintain focus.

> **Recommended demo:** give a banner one action: a button to complete a task, or a link to go somewhere.. Example UI: banner warning: Plan access will end on {Renewal/Expiry date}. Renew now to keep features.; banner info: AI answers can contain mistakes.

### Guide to resolution

If a banner is not dismissible, it should contain a single, highly visible call-to-action button that resolves the state or provides necessary details, guiding the user toward a specific next step. Use a button rather than a link here — resolving the issue is a functional action.

> **Recommended demo:** give a banner that can’t be dismissed one button that resolves the issue.. Example UI: banner warning: Plan access will end on {Renewal/Expiry date}. Renew now to keep features.; banner critical: Your message was not delivered. Please try again..

## Placement

### Top of content area

Do display the banner at the top of the affected content area.

> **Recommended demo:** place the banner at the top of the content it affects.. **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Placement 1. Source asset: `./assets/banners/placement-1.png`.

### Maximum two banners

A single banner is ideal, but if more is needed the max should be no more than two banners in a single view. If a third banner needs to appear, the oldest Success or Informational banner is hidden or dismissed automatically to make room. Critical and Warning banners are never auto-removed — they persist until the user resolves the underlying issue, per their own dismissal rules.

> **Avoid demo:** show more than two banners at once. It adds too much cognitive load.. **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Placement 2. Source asset: `./assets/banners/placement-2.png`.

### Priority stacking order

If there must be two banners, order them by:
Highest priority / Most critical banner (at the very top).
Second highest priority / Second most critical banner (below the first one).
If both banners have the same criticality, the newest or most recently triggered one often takes the top spot, or the decision is made based on which piece of information is most urgent for the user to see first.

> **Recommended demo:** put the most critical banner on top when two banners are showing.. **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Placement 3. Source asset: `./assets/banners/placement-3.png`.

## Accessibility

### Contrast and color independence

Each banner variant's background, text, and icon colors must meet WCAG AA contrast requirements (4.5:1 for text, 3:1 for icons and borders). Never rely on color alone to distinguish variants — the icon and copy tone must independently communicate severity for users with color vision deficiencies.

## Copy

### State status directly

Banner copy must be kept as concise as possible, ideally limited to one main sentence and one actionable sentence. Do use a direct, declarative sentence structure to immediately state the status or risk, avoiding overly polite phrasing, passive voice, or system jargon, thereby maximizing scannability and comprehension.
The tone must be neutral and professional across all types, though it should shift in intensity—firm for Errors, cautious for Warnings, and positive but measured for Success and Information.

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: banner warning: The current lesson could not be saved. Try again when the connection is available.; banner warning: Something technical may be wrong with your HSK AI account; source UsageExample illustration.

### Link problem to solution

For Error and Warning banners, do use copy that clearly states what the user can do next to resolve the issue or mitigate the risk, linking the textual problem statement directly to the intended Call-to-Action button or link.

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: banner critical: Could not connect. Retry after checking your connection.; banner critical: Could not connect.; source UsageExample illustration.

### Include specific data

When applicable, the copy for transactional banners (Success, Warning) must include specific numbers, identifiers, or dates to confirm the impact of the action or the immediacy of the risk (e.g., "2 assignments," or "expires on &#123;date&#125;").

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: banner success: The verified account change has been completed; banner success: Your changes have been saved to your schedule; source UsageExample illustration.

### Punctuation

Copy should omit periods when the message consists of a single, short statement or command. This enhances scannability and maintains a headline style. If the copy requires more than one full sentence, periods must be used to correctly separate those thoughts.

> **Recommended demo:** leave off the period for a single sentence, and use periods when there’s more than one.. Example UI: banner info: If copy is one sentence, no periods; banner info: If copy is more than one sentence, use periods..

### Sentence case

To be consistent with UX copy guidelines, use sentence case.

> **Recommended demo:** use sentence case in banner copy.. Example UI: banner warning: The current lesson could not be saved. Try again when the connection is available..

## HSK AI notification and payment rules

### Verified account and billing status

- Display a payment success or Pro entitlement only after the authoritative backend confirms the relevant payment/entitlement. A banking authorization, checkout redirect, pending verification and captured payment are different states.
- Use server-provided plan, duration, amount and expiry details where available and safe; never make up transaction values or display a personal receipt belonging to a different account.
- A non-critical future subscription reminder may be acknowledged; a current unresolved blocking issue must remain represented in the account state. Dismissing visual UI does not cancel a subscription or change payment status.
- Respect the approved iPhone PWA and Android purchase paths; do not show an unavailable purchase action on the Google Play version or create new payment routes.

### Learning and interface safety

- An error about unsaved lesson progress must clearly state what did not save and how to retry. The app must not report successful completion when the server has not confirmed it.
- Place alerts so they do not cover answer options, Hanzi, pinyin, lesson character feedback, the red AI Voice Orb, navigation, safe areas or the open keyboard.
- Correct/incorrect lesson reactions use the existing characters and lesson feedback, **not** a persistent global banner. Preserve approved animation and feedback behavior.
- Keep the original one- or two-banner limit, severity order, contrast standards and accessibility rules. Treat informative tips and marketing as non-critical, not as false Critical/Warning events.
- On account switch, unload stale learner-specific notices; distinguish stale, verifying, processing, rejected and confirmed states.

### Source demonstrations

Any retained teacher/school or other-brand sample screen is a **historical illustration of the rule** and does not define HSK AI's colors, typography, content or characters. This is documentation only; HSK AI production notification logic is unchanged by this file.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: banners.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/banners.png)

- [banners.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/banners.png) — exact source blob `dce69d4d6091` (illustrated above)
- [copy-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/copy-1.png) — exact source blob `cc3f154bc6c4`
- [copy-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/copy-2.png) — exact source blob `bf820d172ad5`
- [copy-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/copy-3.png) — exact source blob `3b3b40b74108`
- [placement-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/placement-1.png) — exact source blob `081bd66f743c`
- [placement-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/placement-2.png) — exact source blob `fa405f893bbf`
- [placement-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/placement-3.png) — exact source blob `a8946a36eed6`
- [variants-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/variants-1.png) — exact source blob `e230a47f6b40`
- [variants-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/variants-2.png) — exact source blob `ff488b073e9b`
- [variants-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/banners/variants-3.png) — exact source blob `ab35014792a0`
