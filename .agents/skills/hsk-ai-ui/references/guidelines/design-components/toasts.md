> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/toasts.mdx`, Git blob `bc59722b97291623ce16e450ce67a6b1834995c6`; 15 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Visual of a Toast that says 'Students removed' with an undo and dismiss button. Source asset: `./assets/toasts/toasts.png`.

# Toasts

> **HSK AI adaptation:** All original school/teacher screenshots illustrate toast hierarchy and states, not actual HSK AI screens. Keep the professional rules for clear status, recovery, focus and non-blocking feedback. A saved lesson, verified payment or changed subscription must not be announced as successful until the authoritative backend confirms it. An actionable failure should remain discoverable; do not conceal mandatory error details in the optional two-line expand/collapse pattern.

*Component role: System feedback/Transient messages*

A non-intrusive, temporary container used to display brief, passive, and asynchronous system feedback. Toasts communicate success, failure, or neutral information that does not require immediate user action to dismiss or proceed.

## Recommended: When to use

The choice to use a toast is determined by the need for non-blocking, transient system feedback.

| Use when | Example use |
| --- | --- |
| Delivering low-urgency feedback that doesn't interrupt the user's flow | Confirming that a file has been saved successfully in the background. |
| The message is transient and persists only until dismissed or acted on | Confirmation of an actual saved learning preference or completed supported action **after the server confirms it**. |
| No action is required, or only an optional secondary action is available | A verified action-success message; offer Undo only if the HSK AI action truly supports reversal. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| An error blocks user progress or requires an immediate response | Modal or banner (global alert) | Do not use for errors that block user progress, require immediate data validation, or necessitate a response. These require a persistent block or a high-visibility alert. |
| The message requires multiple lines of text or a log of events | Notification center or full page alert | Toasts are for brief, one-line updates. If the message requires multiple lines of text, context, or a log of events, it must be contained in a dedicated, dismissible area. |
| The action is mandatory or high-stakes | Dialog | For feedback requiring mandatory action or complex confirmation (e.g., irreversible deletion, large-scale confirmation). The Toast, even with an action, is not sufficient for high-stakes decision-making. |

## Variants

### Error

Do use for temporary, severe action failures (like a dropped connection) or issues that immediately stop a single action. The Toast provides non-interruptive feedback, and the error must be easily recoverable, typically by simply retrying the action or fixing the connection.
It must NOT include a dismiss 'X' because the error is an active barrier to function; allowing the user to dismiss the alert would cause silent failures if they attempt data-critical actions, as the system status has not actually been resolved.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Two examples of error toasts: 'No internet connection' and 'Answer required. Enter your response before proceeding.'. Source asset: `./assets/toasts/variants-1.png`.

### Success

Do use for non-interruptive, transient confirmation of a completed, successful action. An optional "Undo" action should be provided for reversible operations (e.g., deletion), serving as the primary call-to-action.
It must include a dismiss 'X' because, for non-critical confirmations, the user should be allowed to manually close the alert immediately if they've seen the message, thereby offering full control over their visual interface.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Two success toasts: 'Question saved' with no action, and 'Question deleted.' with an undo action. Source asset: `./assets/toasts/variants-2.png`.

### Informational

Do use for low-priority, non-critical status updates, feature activation, or general, non-urgent announcements. This includes confirming actions like password copy or status changes where a neutral tone is required. The Toast confirms the system state and ensures the user's workflow is uninterrupted.
It must include a dismiss 'X' to allow the user to manually close the non-critical alert before the automatic timer runs out, reducing visual clutter.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Three informational toasts: 'Dark mode active', 'Password copied', and 'Preview mode active. Student data will not be impacted'. Source asset: `./assets/toasts/variants-3.png`.

## States

### Iconography

The toast must include the system-defined type icon. The icon is the most immediate signal, helping users who may have color vision deficiencies or who are scanning the page quickly.
Do not use custom, context-specific icons (a "wifi" for no wifi connection) in the primary position, as this dilutes the meaning of the core status types.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Do: 'critical', 'success', and 'informational' icons. Don't do: other icons.. Source asset: `./assets/toasts/states.png`.

## Placement

### Default viewport location

The source desktop example favors bottom center. In HSK AI iPhone PWA and Android, use **professional mobile placement and visual priority** to avoid bottom navigation, keyboard, safe area, active exercise answers, AI Voice controls and payment actions. The existing placement is a baseline to compare, not mandatory final geometry. No source screenshot is an instruction to obscure primary controls.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** Placement is bottom center overlapping card rather than contained within. Source asset: `./assets/toasts/placement-1.png`.

### Avoidance of critical controls

Toasts must never obscure primary calls-to-action (CTAs) or crucial data fields the user is currently working on.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** Same bottom center placement, but demonstrating how it doesn't overlap any other controls. Source asset: `./assets/toasts/placement-2.png`.

## Interaction

### Not auto-dismissed

Toasts are manually dismissible (do not disappear after a certain time interval). Toasts must remain visible in a view  so that keyboard and screen reader users can reach them.
When they surface error information, they should use aria-live assertive role. When the error needs action, move the focus to the toast.
When they surface success information, they should use aria-live polite role.

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** An informational toast with a dismiss button. Source asset: `./assets/toasts/interaction-1.png`.

### Focus

Toasts must contain only one action.

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** A toast with a single action. Source asset: `./assets/toasts/interaction-2.png`.

### Reversibility

The action should primarily include the "Undo" action whenever the user has performed a destructive or highly reversible operation (e.g., deleting an item).

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** A toast with an undo action. Source asset: `./assets/toasts/interaction-3.png`.

### Action avoidance

Do not include an action link on a Toast when the message confirms an operation that is not reversible or does not require immediate contextual follow-up (e.g., "All changes saved"). In these instances, the Toast should contain text only.

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** Example of a toast with an 'undo' for an undoable operation — add an action to a toast that doesn’t need one, like “Undo” on “All changes saved.”. Type: dont. Source asset: `./assets/toasts/interaction-4.png`.

## Copy

### Brevity

Keep the text label to one line long when possible. This constraint is intended to prevent excessive copy, though the component must be allowed to wrap to two or three lines on smaller screens (e.g., mobile) without truncating the message, thereby preventing the Toast from visually obstructing large parts of the screen.

> **Historical figure 12 — source figure reference (only approved samples, if any, are linked below):** Two toasts. The first is short: 'Question saved'. The second too verbose and wraps to a second line: 'The questions you accepted have been successfully saved'. Source asset: `./assets/toasts/copy-1.png`.

### Use passive voice

Copy should focus on the object affected by the action. Use a noun + past participle structure to confirm a successful outcome. This ensures the most important information appears first

> **Historical figure 13 — source figure reference (only approved samples, if any, are linked below):** Two toasts. 'Students removed' is passive voice and correct. 'Removing students now' is improper voice and verb form.. Source asset: `./assets/toasts/copy-2.png`.

### Punctuation

Copy should omit periods when the message consists of a single, short statement or command. This enhances scannability and maintains a headline style. If the copy requires more than one full sentence, periods must be used to correctly separate those thoughts.

> **Historical figure 14 — source figure reference (only approved samples, if any, are linked below):** Example of correct toast punctuation — leave off the period for a single short statement, and use periods when there’s more than one sentence.. Type: do. Source asset: `./assets/toasts/copy-3.png`.

### Action copy

Action text must be a single, strong verb or short, imperative phrase (e.g., "Undo," "View," or "Try Again") that clearly describes the user's immediate recovery or context. Avoid conversational fillers, technical jargon, or multi-word phrases (e.g., avoid "Click here to view" or "Please reverse the deletion").

> **Historical figure 15 — source figure reference (only approved samples, if any, are linked below):** Two toasts. The first has a proper 'View' action, and a second with 'View link' which is not recommended. Source asset: `./assets/toasts/copy-4.png`.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: copy-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/copy-1.png)

- [copy-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/copy-1.png) — exact source blob `0db047666492` (illustrated above)
- [copy-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/copy-2.png) — exact source blob `cc63264ef97e`
- [copy-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/copy-3.png) — exact source blob `2dddb4551b53`
- [copy-4.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/copy-4.png) — exact source blob `dc164eb2fd62`
- [interaction-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/interaction-1.png) — exact source blob `ae161569e046`
- [interaction-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/interaction-2.png) — exact source blob `8eee88fdf35b`
- [interaction-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/interaction-3.png) — exact source blob `7c7552ab453e`
- [interaction-4.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/interaction-4.png) — exact source blob `767f9a318ed2`
- [placement-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/placement-1.png) — exact source blob `c2db03bffebc`
- [states.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/states.png) — exact source blob `520fd35c6d13`
- [toasts.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/toasts.png) — exact source blob `cdc01a62095e`
- [variants-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/variants-1.png) — exact source blob `6c10b92fcf9b`
- [variants-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/variants-2.png) — exact source blob `7dc3b34c1c49`
- [variants-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toasts/variants-3.png) — exact source blob `44b9d64b6535`
