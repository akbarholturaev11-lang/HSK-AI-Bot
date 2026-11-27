> **HSK AI professional design guideline — portable review copy.** Current implementation is not implied. Source `__docs__/design-components/active-filters.mdx` (Git blob `ca9a5a855efed7adb23e6f2f6f60f841bea714eb`); 4 historic figure references, 0 MDX demo blocks. Approved neutral example PNGs are linked below where available; excluded foreign screens and vendor runtime code were not transferred. The original prose remains an internal source-derived draft. Full professional prose is retained as an internal source-derived draft.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Active filters. Source asset: `./assets/active-filters/active-filters.png`.

# Active filters

> **HSK AI application:** The original images show the source product's school filters as **structural examples only**. In HSK AI, an active-filter label describes a real, removable choice on an available learner list or an authorized report. Preserve the full professional active-filter visual anatomy, chip grouping, label/removal hierarchy, placement and responsive behavior as the target; HSK AI's present styling is an implementation baseline, not a restriction on improvement. Respect actual filter choices and mobile constraints.

*Component role: Active filter feedback*

Compact visual elements that provide transparent feedback on the current dataset. In our reporting interface, they are primarily used to display active filter selections directly below the filter bar.

## Recommended: When to use

The choice to use active filters is determined by the need to provide immediate visibility into how a data view has been narrowed and to allow for modular management of active parameters.

| Use when | Example use |
| --- | --- |
| The user needs to see what filters are currently applied | Showing "HSK level: HSK 3" after the learner explicitly applies an available level filter. |
| Individual filters should be removable without resetting all others | Removing only "Exercise type: Listening" while preserving other actually selected criteria. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| The element represents navigation or view switching | Tabs or segmented controls | Active filters represent transient filter states, not primary page navigation. |
| The element is a static, non-removable label | Status badge | If the element can’t be dismissed, it’s not an active filter — it’s a status indicator. |
| The user hasn’t made a selection yet | No active filter — leave the row empty | Active filters are the result of a selection, not a prompt to make one. |

## What generates an active filter

Not every control in the filter bar produces a chip. The deciding factor is who owns the control's starting value. If the product supplies a default and the control can never be cleared to empty, a value is always present regardless of what the user does — a chip couldn't distinguish an actual choice from the baseline, so none appears. If the user is the one introducing a value at all — the control starts empty or inactive until they act — a chip appears as soon as they do, since its presence signals a real, removable choice.

| Control type | Generates an active filter? | Why |
| --- | --- | --- |
| Standard dropdown or inline filter button | Yes | Starts empty or inactive — any value present means the user chose it. Long or multi-value selections also get truncated or summarized as a count on the control itself (e.g. "Long optional category…", "2 selected"); chips restore full legibility, one per value when multiple are selected. |
| Embedded filter dropdown (e.g. Date, defaulting to Last 30 days) | No | The product supplies a default and the control can't be cleared to empty — a value is always present regardless of user action, so a chip couldn't signal an actual choice. |
| Date inline filter button | Yes | No date is pre-applied — the control starts empty until the user adds one. Its presence, even when short and fully legible on the control itself (e.g. "Nov 1 – Nov 30"), signals a real, removable choice the user made. |
| Search field | No | The typed term is fully visible in the field itself. |
| Toggle | No | Its on/off state is a complete, unambiguous indicator, always visible on the control. It still counts as a filter the user applied, so Clear all filters turns it off. |
| Segmented control | No | The selected segment stays fully visible and highlighted on the control itself. |

## States

Each active filter displays the filter category and its selected value — for example, "HSK level: HSK 3." A dismiss icon allows the user to deactivate that specific filter.
When more active filters exist than can fit on one line, they wrap to a second line to maintain full transparency.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** A report filter bar with search, date, and school controls, above five active filter pills that wrap onto a second line, each showing a category and value with a dismiss icon, followed by a Clear all filters link. Source asset: `./assets/active-filters/states.png`.

## Placement

Active filters sit directly below the filter bar, creating a clear visual link between the controls and the data they affect.
They sit above the data visualization — cards, charts, or tables — acting as a bridge between the filtering interface and the displayed data.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** A report page showing active filter pills positioned directly below the filter bar and above the results count and data area. Source asset: `./assets/active-filters/placement.png`.

## Copy

Use the format [Category]: [Value] — for example, "HSK level: HSK 3." This ensures users can immediately understand what each chip represents without needing to open the dropdown to check.

For multi-select filters, each selected value gets its own chip rather than combining them into one — "HSK level: HSK 3" and "HSK level: HSK 4" as two chips, not one combined label. This keeps each value individually scannable and removable.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Copy. Source asset: `./assets/active-filters/copy.png`.

## HSK AI product application

### HSK AI application

- Display removable filter labels **only for actually selected, optional criteria**. A fixed selected HSK course or required default scope is not automatically an active removable filter.
- The source figure shows the position, not HSK AI colors or Khan Academy subject labels. On phones, wrap labels, keep a clearly named removal control and prevent labels from covering the result count.
- Removing one selected criterion must retain other filters, any typed search and the sort order. Keep the resulting count consistent with the listed records.
- Use the approved HSK AI touch targets, iconography and readable labels; do not represent lesson progress or Pro status as an active filter if it is merely a static badge.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: active-filters.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/active-filters/active-filters.png)

- [active-filters.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/active-filters/active-filters.png) — exact source blob `b986b2d68d6a` (illustrated above)
- [copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/active-filters/copy.png) — exact source blob `bf9fa2fb3e5d`
