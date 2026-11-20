> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/modals.mdx`, Git blob `9c3327581a0ae2fd5242adb8a794ea3e1bb1d735`; 16 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Modals. Source asset: `./assets/modals/modals.png`.

# Modals

> **HSK AI scope:** The original screenshots explain modal structure and interaction, not HSK AI's approved visual style. On iPhone PWA and Android, preserve the **professional modal anatomy, hierarchy, scrim, spacing, adaptive placement and focus/dismissal semantics** as the target. Choose centered confirmation, sheet or full-screen presentation by task and available mobile space; do not freeze today's visual style. Preserve protection against lost lesson progress, mistaken account changes and interrupted payment verification.

*Component role: Focused task or decision*

A high-focus container used to isolate a user’s attention for a specific sub-task or critical decision. Modals require an explicit action or dismissal before the user can return to the primary background content.

## Recommended: When to use

The choice to use a modal is determined by the need for complete user focus and the "sandboxing" of a specific workflow.

| Use when | Example use |
| --- | --- |
| A high-stakes decision requires the user’s full attention | Confirming exit from an unfinished lesson. |
| The task is important but must not leave the page or take up a full-page view | Changing a supported HSK AI learning preference. |
| The system requires an explicit "Confirm" or "Cancel" before proceeding | Restarting an exercise or confirming a deletion. |
| A short sequential flow is needed without leaving the page | A short supported account or study setup sequence. |
| Supplementary content is needed without fully navigating away from the current page | Explaining a Chinese learning concept without abandoning the lesson. |

## Avoid: When NOT to use

Avoid modals when the task doesn’t require the user’s full attention, when the content is too complex to contain, or when a lighter in-context interaction would be less disruptive.

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| The user needs to reference or monitor background content | Side drawer | Don’t use a modal if the user needs to glance at background context, or if the information is supplemental (e.g., optional lesson details) and should coexist with the main task. The side drawer is not yet documented in this system; treat this as known design debt. |
| The content is dense or complex enough to need its own page | Full page or side drawer | If the task requires significant scrolling, more complex multi-step flows, or heavy content, it belongs on its own page — not inside a modal. |
| The interaction is a simple binary choice or lightweight edit | Popover | Don’t use a modal for a single binary choice or a simple rename; it’s too interruptive for "light" actions. |
| A modal is already open | Redesign the flow | Never stack task modals. A second modal that introduces new content or choices disorients the user and breaks their sense of where they are. The one exception is a confirmation that resolves the dismissal of the modal beneath it — see Dismissal and unsaved state. |

## Variants

Modals are a universal container, but their internal logic changes based on the user’s goal. The following sections detail the modal flavors used across the product.

### Confirmation

Use for destructive or non-reversible actions.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** A “Start over?” confirmation modal centered over a dimmed exercise page, warning that starting over clears progress, with Start over and Keep going actions. Source asset: `./assets/modals/confirmation-flow.png`.

### Functional task

Use for short supported study preferences, account settings or configuration tasks.

Multi-step flows have additional requirements — see Multi-step flows under Interaction.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** An “Add your students” modal over a dimmed roster page, offering class-link, manual, and Google Classroom import options with Cancel and Continue. Source asset: `./assets/modals/functional-task-flow.png`.

### Selection (configuration)

Use for complex, multi-faceted filtering or export settings.

See [Modals - selection](modals-selection.md).

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** A “More filters” modal over a dimmed report, with display options, course, subject checkboxes, and practice fields, plus Reset filters and Apply filters. Source asset: `./assets/modals/selection-flow.png`.

### Contextual education

Triggered by info icons. Keeps the explanation local to the context.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** A “Mastery learning” explainer modal over a dimmed page, describing what mastery learning is and how it is scored, with a Got it button. Source asset: `./assets/modals/contextual-education-flow.png`.

### Marketing and announcement

Use only for approved HSK AI feature announcements with a justified interruption, respecting the existing per-session suppression and non-interruption rules.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** A visual “Check out your new collection!” announcement modal, badged “New”, with a colorful accessory grid, a “New unlock” label, and a Customize Khanmigo button, over a dimmed page. Source asset: `./assets/modals/marketing-flow.png`.

### Media

Always read-only — no footer actions.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** A read-only media modal showing a Gauguin painting on the left with its title, attribution, and description on the right — no footer actions. Source asset: `./assets/modals/media.png`.

## Usage and purpose by variant

| Variant | Purpose | Example |
| --- | --- | --- |
| Confirmation | To verify a high-stakes or permanent action and prevent errors. | Deleting an account or discarding unfinished study work. |
| Functional task | To complete a sub-task or data entry without leaving the page. | Selecting or confirming a supported lesson setting. |
| Selection (configuration) | To narrow down or configure exactly what is being viewed. | Applying supported filters to recorded lesson history. |
| Contextual education | To provide rich, on-demand explanation of a specific term or feature. | Clicking an (i) icon for "What is mastery?" |
| Marketing and announcement | To drive adoption of new features or highlight system value. | Introducing an approved HSK AI feature without interrupting an active lesson. |
| Media | To display rich media alongside contextual detail. | Expanding an artwork to view its full description. |

## Sizing reference

Choose a fitting presentation according to the task and mobile viewport, rather than copying fixed 400–800px school-dashboard dialog widths. The original sizing principle remains: important text and decisions must remain in one focused readable area.

| Variant | HSK AI mobile placement | Reason |
| --- | --- | --- |
| Confirmation | Compact centered dialog within available safe area | Two clear choices and their consequences stay together. |
| Contextual education | Compact dialog or bottom sheet chosen by professional content hierarchy, task and phone constraints | Gives help without covering the entire lesson. |
| Functional task | Short bottom sheet; separate full-screen view for long forms | Supports keyboard and input without hidden controls. |
| Selection | Bottom sheet with scrollable body and reachable footer | Makes multiple choices usable on narrow phones. |
| Feature announcement | Approved HSK AI presentation only | Avoids unsolicited interruptions during study. |
| Media | Responsive viewer or full-screen display | Keeps images legible and prevents clipping. |

Use the existing PWA/Android surface and spacing tokens. Respect iPhone safe areas, Android system insets, keyboard height and enlarged text.

## Surface and elevation

A floating modal uses HSK AI's approved raised surface with sufficient separation and a full background scrim. It is never opened as an apparently interactive floating panel with a live clickable background. Full-screen media is a dedicated viewer rather than a centered floating dialog. The Media variant is the exception: it fills the viewport rather than sitting centered over the scrim. See [Surfaces and elevations](../design-foundations/surfaces-and-elevations.md).

| Element | Value | Token |
| --- | --- | --- |
| Modal container | Approved HSK AI raised surface | Verified HSK AI semantic surface roles; improve visual elevation in the later UI pass |
| Container elevation | Enough separation for a distinct dialog | Verified roles where suitable; professional elevation is the design target |
| Background | Modal scrim | Verified scrim role or explicitly proposed role, never an invented implemented token |

## Placement

### Adaptive placement

Use centered placement for compact confirmations and the established mobile bottom-sheet pattern for short selections, options and input. Both must cover and deactivate the underlying interface with a full scrim. A longer flow needs its own screen. The media viewer may fill the viewport.

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** A modal centered horizontally and vertically in the viewport over a darkened page, with crosshair guides showing the center alignment. Source asset: `./assets/modals/placement-centered.png`.

### Actions always reachable

Keep the primary and secondary choices at the dialog or sheet footer, outside the scrolling body. On narrow phones, a single primary action can fill the available width; multiple buttons can stack or sit side by side when text fits. Maintain a logical reading order and a genuine safe escape path. Read-only media does not need footer actions.

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** A modal with its primary and secondary actions anchored to the bottom-right corner, highlighted with a dashed outline. Source asset: `./assets/modals/placement-actions.png`.

### Overflow

A modal fits within the usable visual viewport including keyboard, safe area and system bars. Its content height may grow only within that space. Past that point the body scrolls while the title and the actions stay pinned — the user must never have to scroll to reach the primary action.

Background content does not scroll while a modal is open. Scrolling the overlay scrolls nothing.

## Interaction

### Focus

Opening a modal moves focus into it — to the first interactive element, or to the modal itself when the content is read-only. While the modal is open, focus is trapped inside it: tabbing past the last element returns to the first, and background content is unreachable by keyboard.

Closing the modal returns focus to the element that opened it, so a keyboard user resumes where they left off rather than at the top of the page.

The modal is exposed to assistive technology as a dialog, labelled by its title, with background content hidden.

### Dismissal and unsaved state

Users can leave through an accessible close/back route. Outside-tap and Escape/system-back dismissal are allowed only when safe for the current task. Active lesson exit, unsaved input, account deletion and payment confirmation must not silently discard data or change financial state. Warn before dropping unsaved functional-task input.

This confirmation is the only permitted second layer. It resolves the dismissal of the modal beneath it and nothing else — it introduces no new task, offers no route to a third layer, and on resolution either returns the user to the modal they were in or closes both.

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** A “Discard changes?” modal warning that unsaved changes will be lost, with a Keep editing button and a red Discard button. Source asset: `./assets/modals/interaction-dismissal.png`.

### Multi-step flows

A modal can support a short sequential flow of 2–3 steps when each step is simple and self-contained. If the flow grows beyond 3 steps or requires significant input at each stage, move it to a full page with the [Progress stepper](progress-stepper.md) instead.

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** Step one of an “Add your students” multi-step modal, selecting an import method before continuing to the next step. Source asset: `./assets/modals/interaction-multistep.png`.

## Buttons

### Pairings

Modal actions use the [Buttons](buttons.md) hierarchy. Source-product-specific button appearance is not required in HSK AI. Three pairings apply:

-   **Standard (Primary + Secondary):** used for neutral functional tasks (e.g., "Save preference"). The secondary button (outlined) provides a clear, accessible exit that feels equal in importance to the task.
-   **Nudge (Primary + Tertiary):** used for confirmations. The primary solid button represents the "path of least resistance." Whether this is the safe choice or the requested action depends on the risk involved (see Directional logic).
-   **Destructive (Danger + Tertiary):** used for permanent actions. The destructive action uses the distinct Critical color (e.g., "Delete account") and "Cancel" is a Tertiary button to highlight the severity.

> **Historical figure 12 — source figure reference (only approved samples, if any, are linked below):** Three button pairings: Standard (Cancel + blue Save), Nudge (Reset filters + blue Apply filters), and Destructive (Cancel + red Delete class). Source asset: `./assets/modals/buttons-pairings.png`.

### Directional logic

-   **High-risk nudges:** when an action results in a loss of progress (e.g., "Start over"), the Primary button pivots to the safe/positive action (e.g., "Keep going"). This prevents "auto-pilot" clicks from causing accidental data loss.
-   **Standard intent:** when an action is neutral or expected (e.g., "Log out"), the Primary button remains the requested action. Since there is no data loss to prevent, the system respects the user’s explicit command to exit.

> **Historical figure 13 — source figure reference (only approved samples, if any, are linked below):** Two examples: a high-risk nudge where Keep going is the primary button next to a Start over link, and a standard case where Logout is primary next to a Cancel link. Source asset: `./assets/modals/buttons-directional.png`.

## Copy

### Headline titles

Modal titles should be direct and specific — ideally a noun or short noun phrase that describes exactly what the modal is for. Avoid generic titles like "Are you sure?" or "Notice."

> **Historical figure 14 — source figure reference (only approved samples, if any, are linked below):** Recommended specific titles like “Start over?”, “Delete assignment?”, and “Add student” versus discouraged generic titles like “Are you sure?”, “Warning”, and “Notice”. Source asset: `./assets/modals/copy-headline.png`.

### Describing body content

The body copy should explain the consequence of the action clearly and concisely. For destructive actions, be explicit about what will be lost. Never rely on the title alone to carry the full context.

> **Historical figure 15 — source figure reference (only approved samples, if any, are linked below):** Recommended body copy “Starting over will clear your current progress. This cannot be undone.” versus the discouraged vague “Are you sure you want to do this?”. Source asset: `./assets/modals/copy-body.png`.

### Action labels

Use explicit verbs that describe exactly what will happen. The user should be able to read the button label alone and understand the outcome. Avoid generic labels that require reading the full modal to understand.

> **Historical figure 16 — source figure reference (only approved samples, if any, are linked below):** Recommended explicit action labels (Start over / Keep going) versus discouraged generic labels (No / Yes). Source asset: `./assets/modals/copy-actions.png`.

## HSK AI implementation safeguards

- Keep focus inside the active dialog and restore it to the triggering control on close, using the platform's accessibility behavior. Underlying buttons, navigation and scroll must be inactive while the modal is open.
- Prevent unrelated announcements and payment inbox overlays from stealing focus from an active lesson, form, checkout or AI Voice interaction.
- Preserve existing HSK AI leave-lesson/Back confirmation when a run is active, and existing keyboard/safe-area behavior. Do not treat the source school's screenshots or desktop sizes as required PWA/Android appearance.
- Destructive actions use the semantically distinct Critical palette, not the ordinary HSK AI brand-red primary style. In high-risk decisions, emphasize the safe choice to reduce accidental data loss.
- A dialog may support two or three short steps; long workflows should be dedicated screens. Avoid stacking task dialogs, except one focused confirmation that resolves dismissal of the underlying dialog.
- This file does not change production app screens; later implementation must verify existing components and tests first.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: buttons-directional.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/buttons-directional.png)

- [buttons-directional.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/buttons-directional.png) — exact source blob `a59bc5ea62f8` (illustrated above)
- [buttons-pairings.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/buttons-pairings.png) — exact source blob `c3eeaae373b6`
- [copy-actions.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/copy-actions.png) — exact source blob `813144c3d246`
- [copy-body.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/copy-body.png) — exact source blob `388787fdaf0f`
- [copy-headline.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/copy-headline.png) — exact source blob `87e8335b3b33`
- [interaction-dismissal.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/interaction-dismissal.png) — exact source blob `633895577783`
- [modals.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/modals.png) — exact source blob `a1ba7d7b5be7`
- [placement-actions.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/placement-actions.png) — exact source blob `076ad73c100f`
- [placement-centered.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals/placement-centered.png) — exact source blob `93e7b64a1b4a`
