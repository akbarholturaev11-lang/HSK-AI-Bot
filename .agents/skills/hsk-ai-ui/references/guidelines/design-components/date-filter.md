> **HSK AI professional design guideline — portable review copy.** Source: `__docs__/design-components/date-filter.mdx`, Git blob `070428cd7b03b8a5756d45c52b1877244116b634`. 7 historic figure references and 0 MDX demo blocks; source images / vendor runtime code were not copied. Source prose remains an internal derivative draft pending rights and detailed visual parity review; this does not assert a live app feature.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Date filter. Source asset: `./assets/date-filter/date-filter.png`.

# Date filter

> **HSK AI application:** The source illustrations explain **default date scope versus optional date filtering**. Use this distinction only where HSK AI actually supplies date-based lesson history or authorized analytics. Never copy the source school-dashboard appearance or force a date filter onto a view without temporal data.

*Component role: Temporal filtering*

A dropdown component for filtering data across a range of time. Offers predefined relative options (Today, This week, Last 30 days) and a custom range entry for freeform input.

## Recommended: When to use

The choice to use a date filter is determined by the need to filter data based on a specific point in time or a span of time (date range).

| Use when | Rule | Example use |
| --- | --- | --- |
| Filtering by a time period | Used when the primary dataset needs to be restricted to a specific time context | Filtering supported learning history or authorized analytics to a valid selected period |
| Comparing across time periods | Used when the user needs to select a period to conduct time-based analyses and identify trends | Comparing a verified learner metric in two comparable available periods |

## Avoid: When NOT to use

| Don't use when | Recommended alternative | Rationale |
| --- | --- | --- |
| Filtering non-date attributes | Filter or dropdown | Do not use a Date Filter to select non-temporal data (e.g., HSK level, vocabulary or exercise type) |
| Sorting a list by date | Sort toggle | If the need is simply to sort a list by 'Date Created' or 'Due Date', a simple sort control is less disruptive than a full picker interface |
| Selecting a specific date or deadline | Date picker | Picking a deadline or birthdate requires a specific point in time, not a range |

## Variants

### Date filter

The product pre-applies a date. Data is always scoped to a time period — the user never sees an unfiltered state. They can change the selection, but cannot clear it entirely.
Use this when there are pages where showing all-time data would be overwhelming or meaningless — e.g. a real activity summary whose authorized data is deliberately limited to a documented current period. The product owns the initial state.
There is always a value in the trigger. If no user selection has been made, the product default shows (e.g. Today).
Because the product supplies this default and the control can never be cleared to empty, changing the selection does not generate an active filter chip (see Active filters).

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** A basic example of a Date filter opened with the first `Today` option selected, followed by `This week` and `Last 30 days`, each with the actual accompanying date or date range as subtext. At the bottom is a `Custom Range` affordance after a horizontal separator.. Source asset: `./assets/date-filter/variants-1.png`.

### Date inline filter button

No date is pre-applied. Data defaults to all time. The user chooses to add a date filter — clicking the inactive inline filter button opens the same predefined options. Once applied, the button shows the active range and gains a clear (×) control.
Use this when there are pages where all-time data is a valid and expected default — e.g. a genuinely available lesson-history list where the learner may optionally select a period. The user owns the initial state.
The × control clears back to all-time (unfiltered). This is the key distinction from the standard variant — this one can be cleared.
Because no date is pre-applied, any value shown here was chosen by the user. Applying one generates an active filter chip, even though the range is already visible on the button itself (see Active filters).

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Shows the transition of an empty `Date` filter being filled in. Once filled in, a calendar icon appears at the start of the input followed by the range and then a `clear` icon affordance. Source asset: `./assets/date-filter/variants-2.png`.

### Key differences

| Property | Date filter | Date inline filter button |
| --- | --- | --- |
| Initial state | Product applies a default (e.g. Today) | No date applied – show all-time data |
| Who sets the first value | The product | The user |
| Can be cleared | No – always has a value | Yes – X returns to all-time |
| Trigger appearance | Full-width dropdown with current value | Inactive until user adds filter, once selected becomes active state of inline filter button |
| Options on open | Today / This week / Last 30 days / Custom range | Today / This week / Last 30 days / Custom range |
| Generates an active filter chip | No | Yes |

## Placement

In dashboards with multiple filter types, place the date filter leftmost — it is typically the highest-priority filter. Maintain consistent placement across views so users don't have to reorient when switching between reports.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** An example showing the `Date` filter aligned first before `School` and `Grade`. Source asset: `./assets/date-filter/placement-1.png`.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** An example of an empty `Date` filter aligned first before `School` and `Grade`. Source asset: `./assets/date-filter/placement-2.png`.

## Interaction

### Custom range applied

Selecting "Custom range" opens a date picker. Once the user applies dates, the filter updates — the selected range replaces the trigger label and is added to the list as the active selection.
If a new custom range is selected, the previous one does not stay there but is replaced by the newly selected range.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** An example of correct usage. Source asset: `./assets/date-filter/interaction.png`.

## Copy

For dropdown list labels, show a compact, unambiguous date in the learner’s selected locale (for example, "Dec 12" in English). This helps users confirm the right period without requiring a US-style month/day format across all HSK AI languages.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** One correct usage example with 'Dec 1 - Dec 23' and an incorrect one with '12/1 - 12-23'. Source asset: `./assets/date-filter/copy.png`.

## HSK AI product application

### HSK AI dates and mobile presentation

- Show the **actual date interval** behind relative labels such as Today, This week and Last 30 days when available. Use the relevant account/reporting time zone and consistent inclusive/exclusive boundaries; never miscount a lesson near midnight or across time zones.
- The source English month/day formatting is an example for that locale, **not a mandatory date format for HSK AI's supported languages**. Use the learner's localized readable dates while preserving the same selected period.
- A default required date scope is not cleared as an optional filter. An optional added date filter can be removed to restore the correct all-time scope. Preserve the original selection and clear/reset rules.
- A date picker or custom range must fit a phone, safe areas and keyboard. Do not add unsupported historical periods or imply cross-platform metrics are complete when coverage is partial.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-filter/copy.png)

- [copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-filter/copy.png) — exact source blob `4408003a6dd2` (illustrated above)
- [date-filter.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-filter/date-filter.png) — exact source blob `1a71feccf89c`
- [interaction.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-filter/interaction.png) — exact source blob `c01da37913e6`
- [variants-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-filter/variants-1.png) — exact source blob `622d0fa717b3`
- [variants-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/date-filter/variants-2.png) — exact source blob `858ca1fdac0c`
