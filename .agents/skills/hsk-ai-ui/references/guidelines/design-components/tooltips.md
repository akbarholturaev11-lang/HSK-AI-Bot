> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/tooltips.mdx`, Git blob `e40d2f42cfa1da560fa74e7a174195ea492a3ca7`; 6 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Historical source example of short labels that appear beside an icon control; not an HSK AI screen. Source asset: `./assets/tooltips/tooltips.png`.

# Tooltips

*Component role: Contextual identifier*

A small, transient, **non-interactive** text label on a supported hover/focus-capable device. **HSK AI rule:** do not hide required Chinese-learning text, an error, payment disclosure or a needed action in a tooltip. On iPhone PWA and touch-only Android interfaces, use a persistent accessible label or supported contextual help. The upstream figures are historical structural references, not HSK AI product screens.

## Recommended: When to use

The choice to use a tooltip is determined by the need to provide immediate, supplemental context or identification for a UI element without permanently occupying space in the layout or diverting the user from their current workflow.

| Use when | Example use |
| --- | --- |
| Labeling a UI element that has no visible text | Labeling an icon button, such as a "plus" icon with "Add item". |
| Providing more in-depth details about a feature or value | Describing the specific value or impact of a feature in a dashboard. |
| Identifying a non-interactive short datum | Briefly naming a verified value when an adjacent persistent label already carries essential meaning. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| The information is critical to the user’s task | Inline help text | Never hide essential instructions, error messages, or required formatting rules behind a tooltip; users may miss them if they do not hover. |
| Designing for mobile or touch devices | Persistent label | Tooltips rely on hover states, which are unavailable or inconsistent on touch devices; prioritize visible text for mobile-first designs. |
| The text is already visible on screen | No tooltip | Do not use a tooltip to repeat text that is already clearly visible on the screen (e.g., a button already labeled "Save" does not need a "Save" tooltip). |
| Displaying a list of actions or a complex form | Popover | If you need to provide a list of many actions or complex forms, tooltips are too transient; use a Menu or Popover instead. |
| Presenting rich content like links, icons, or illustrations | Menu or popover | Do not use tooltips for large bodies of content. Use Popovers to display more extensive information, including rich text, links, icons, and illustrations. |

## Placement

Position the optional tooltip using the approved **4-unit spacing scale** (typically an 8 CSS px reference gap), adjusted for the actual anchor and screen geometry. The historical source used 6px; **that is not HSK AI spacing policy**. Prefer placement above/below, flipping before clipping into a safe area, keyboard or screen edge. Do not interpret this design gap as a verified current CSS/Android token.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** A “Back” tooltip appearing below the back chevron at the top-left of a practice screen for “Number of solutions to equations”. Source asset: `./assets/tooltips/placement-1.png`.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** A “Start over” tooltip appearing below the reset icon near the top-right of the same practice screen. Source asset: `./assets/tooltips/placement-2.png`.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** A “Check answer” tooltip flipped to the left of the Check button in the bottom-right corner, avoiding the viewport edge. Source asset: `./assets/tooltips/placement-3.png`.

## Interaction

-   **Trigger:** On devices that genuinely support hover, appears on hover and keyboard focus. A touch-only action must not rely on this as the sole explanation.
-   **Dismissal:** Must be dismissible via Escape or moving focus away; ensure the tooltip does not obscure the currently focused action or an HSK question.
-   **No manual trigger:** Tooltips should not require a click to open; if a click is required, use a Popover instead.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** A “Browse library” tooltip anchored to the right of the highlighted library icon in the left navigation rail, beside a grid of subject cards. Source asset: `./assets/tooltips/interaction.png`.

## Copy

### Text limits and formatting

Keep messaging brief and non-interactive; prefer a short phrase. Use inline help, a dialog or a popover when the explanation needs more than a quick identification.

Do not use unnecessary end punctuation for brief tooltip labels. A tooltip does not substitute for the **two-line optional explanation disclosure**: only supporting explanation may collapse, with an accessible top-right ⌄/⌃ icon that opens it in place.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** A tooltip whose text wraps onto three lines and ends with a period: "When you’ve selected your answer(s), click this button to check your answer." — let tooltip text wrap across multiple lines or end with punctuation.. Type: dont. Source asset: `./assets/tooltips/copy.png`.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/tooltips/copy.png)

- [copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/tooltips/copy.png) — exact source blob `bef8a6979740` (illustrated above)
- [tooltips.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/tooltips/tooltips.png) — exact source blob `644434d4296f`
