> **HSK AI professional design guideline — portable review copy.** Source: `__docs__/design-components/date-picker.mdx`, Git blob `d23f47f6f18aabb61228a3b3993bf8f1cd29bd5f`. 4 historic figure references and 0 MDX demo blocks; source images / vendor runtime code were not copied. Source prose remains an internal derivative draft pending rights and detailed visual parity review; this does not assert a live app feature.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Date picker. Source asset: `./assets/date-picker/date-picker.png`.

# Date picker

*Component role: Point-in-time selection*

A text input paired with a calendar popover for selecting a specific date. Supports direct keyboard entry and point-and-click calendar selection.

## Recommended: When to use

The choice to use a date picker is determined by the need to select a specific date — either to filter data or to set a value, such as a due date or event date.

| Use when | Example use |
| --- | --- |
| The user needs to select one exact date | Choosing an exact date in a **supported** HSK AI date-based workflow, such as a real analytics date filter where available. |
| The user needs to schedule an event or reminder on a precise date | Setting a test date in a course calendar. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| Filtering by a relative time period | Date filter | Relative options like "Today" and "This week" are faster for analytics contexts. |
| Only month and year are needed | Dropdown (MM/YY) | A full calendar is overkill when day-level precision isn’t needed. |
| Date and time are both needed | Date time picker | This component handles dates only — no time selection. A combined date and time picker is not yet part of the system; treat this as known design debt rather than an available alternative. |

## Variants

Both variants use a calendar icon, never a caret. The icon signals that a calendar popover will open — a caret would imply a dropdown list.

### Stand-alone date picker

A text input with a calendar icon. The user can type directly in MM/DD/YYYY format or click the calendar icon to open the popover. Used for due dates, event scheduling, or any field requiring a single specific date.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** A "Due date" field showing 05/04/2026, with an open calendar popover for May 2026 and the 4th circled as the selected day. Source asset: `./assets/date-picker/standalone.png`.

### Date picker in custom range modal

Used inside the date filter’s "Set custom range" modal. Two date picker inputs — From and To — each with a calendar icon. This variant only appears inside the date filter modal, never stand-alone. See the [Date filter documentation](date-filter.md) for full context.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** A “Set custom range” modal with From (December 1, 2025) and To (December 23, 2025) date picker fields and an Apply button. Source asset: `./assets/date-picker/custom-range-modal.png`.

## Date constraints

Not every date is selectable in every context. Where a date is constrained, express the constraint in the calendar itself rather than letting the user make an invalid choice and correcting them afterward.

| Constraint | Behavior |
| --- | --- |
| To must not precede From | In the custom range modal, the To calendar disables every date earlier than the selected From date. If the user changes From to a date later than the current To, clear the To value rather than silently reordering the two — reordering reassigns a date the user chose as a start and relabels it as an end. |
| Unavailable dates | Render disabled dates dimmed and in place, never removed. Keeping them in the grid preserves the shape of the month so the user can still orient by week. Disabled dates are not focusable and are exposed to assistive technology as unavailable. |
| Dates outside an allowed range, typed directly | Accept the keystrokes as the user types and surface the problem when the field is committed, rather than blocking mid-entry. Partial input is not yet a wrong answer. |

## Interaction

Users can type directly (MM/DD/YYYY) or click the calendar icon to pick visually. The two entry methods must stay in sync — typing a valid date highlights it in the calendar, and clicking a date updates the text field immediately.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** A "Due date" field mid-entry showing "05/04" with a text cursor, while the calendar popover for May 2026 highlights the 4th in sync with the input. Source asset: `./assets/date-picker/interaction.png`.

## Copy

Label the field for the date being set, not the control — "Due date", not "Date picker" or "Select a date". Use sentence case and no ending punctuation.

Use MM/DD/YYYY as the placeholder so the expected format is visible before the user types. Do not rely on a label or helper text alone to communicate format.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: custom-range-modal.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-picker/custom-range-modal.png)

- [custom-range-modal.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-picker/custom-range-modal.png) — exact source blob `5f4c943aadc4` (illustrated above)
- [date-picker.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-picker/date-picker.png) — exact source blob `8aa266563dfa`
- [interaction.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-picker/interaction.png) — exact source blob `434d3642b037`
- [standalone.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-picker/standalone.png) — exact source blob `1b3cfb16561c`
