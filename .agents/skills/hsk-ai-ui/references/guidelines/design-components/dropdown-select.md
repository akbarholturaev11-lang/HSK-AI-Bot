> **HSK AI professional design guideline — portable review copy.** Source: `__docs__/design-components/dropdown-select.mdx`, Git blob `0c733c01205074674e9064b1597e13d7b7d7c874`. 18 historic figure references and 0 MDX demo blocks; source images / vendor runtime code were not copied. Source prose remains an internal derivative draft pending rights and detailed visual parity review; this does not assert a live app feature.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Dropdown select. Source asset: `./assets/dropdown-select/dropdown-select.png`.

# Dropdown select

> **HSK AI application:** The source dropdown examples show professional selection, accessibility and feedback behavior, not HSK AI school screens. Preserve the source's complete professional dropdown geometry, visual grouping, selection, focus, menu alignment and commit/cancel contract as the **target**; map it onto **only the real options** available in a course, learning-preference form or supported report. Existing HSK AI styling is a baseline to improve, not a reason to drop the professional details.

*Component role: Predefined list selection*

A selection control used in forms, modals, settings panels, and filter bars. Can start empty or with a product default. Single-select and multi-select variants.

## Recommended: When to use

The choice to use a dropdown is based on the need to select from a predefined list of options — either one value or multiple.

| Use when | Rule | Example use |
| --- | --- | --- |
| Selecting a single value | One option must be chosen from a list. | Selecting a course in a filter bar or form. |
| Selecting multiple values | More than one option can be chosen simultaneously. | Selecting several supported exercise types in a filtered view, when that multi-select is implemented. |
| List is too long for radio buttons or checkboxes | More than 8 options. | Selecting from a long available vocabulary category list, if that selector exists. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| Eight or fewer options exist and the user needs to compare them (unless part of the filter bar) | Radio buttons or checkbox group | Visible options reduce clicks and cognitive load. The filter bar is the exception: horizontal space is shared across several controls, so options stay collapsed until requested even when the list is short. |
| The user is opting in to filter | Inline filter button | An inline filter button is added to the bar by the user and can be removed again. A dropdown select is placed there by the product and stays. |
| Filtering by a time period | Date filter | The date filter handles temporal filtering with predefined relative options. |

## Exposed or dropdown

- 8 or fewer — exposed by default.
- More than 8 — dropdown.
- Top filter bar — always a dropdown, regardless of count.

A dropdown is also acceptable at eight or fewer outside the filter bar — a settings page or a long form — where the control is one field among many and the user is setting a value they already know. Expose when seeing the options is part of the decision. Collapse when the user arrives knowing the answer and the surrounding form needs to stay scannable.

## In the filter bar

The filter bar holds two controls that look alike once opened. The difference is who decided the filter is there.

A dropdown select is a dimension the product places in the view — such as an actual course, HSK level or date scope, when required. It is always visible, whether or not it currently holds a value, because the view is defined in terms of it.

An inline filter button is a filter the user opts into. It is not in the bar until they add it. Activating it opens a menu that looks and behaves like a dropdown select, which is why the two are easy to confuse once open — but it can be removed entirely, and the view is complete without it.

The test: if the view cannot be described without the dimension, it is a dropdown select. If the user introduced it, it is an inline filter button.

Whether either control produces an active filter is a separate question, decided by whether it carries a product default. See [Active filters](active-filters.md).

The inline filter button has its own [documented guideline](inline-filter-button.md). Use it for optional rather than required filtering.

## Variants

### Label above

The field label sits above the input. Used in forms and modals where vertical space allows and the label needs to be prominent.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Two stacked dropdowns with their labels above the field: a “Course” dropdown showing the placeholder “Select a course” and a “State” dropdown showing “Algebra 1”. Source asset: `./assets/dropdown-select/label-above.png`.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** A placeholder tile reading “Example coming soon”. Source asset: `./assets/dropdown-select/example-coming-soon.png`.

### Label inline

The label sits inside the field to the left of the value. Used in filter bars and compact layouts where horizontal space is shared across multiple fields.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Two inline-label dropdowns: an empty “Select a course” and one reading “Course: Algebra 1” with the label inside the field. Source asset: `./assets/dropdown-select/label-inline.png`.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** An inline-label “Course: Algebra 1” dropdown highlighted within a report’s top filter bar, alongside Search report, School, Grade, and More filters. Source asset: `./assets/dropdown-select/label-inline-filter-bar.png`.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** An inline-label “Course: Algebra 1” dropdown highlighted inside a “More filters” modal, below the Display options toggles. Source asset: `./assets/dropdown-select/label-inline-modal.png`.

### Single-select

One option can be selected. Selecting an option commits it immediately and closes the menu. In a form this sets the field value; in a filter bar it re-queries the data. An accessible checked indicator marks the selected item using HSK AI's approved semantic colors and icons; do not copy the source product's blue palette.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** An open single-select menu listing Geometry 1, Algebra 1, and Algebra 2, with Algebra 2 marked active by a filled blue checkmark circle. Source asset: `./assets/dropdown-select/single-select.png`.

### Multi-select

Multiple options can be selected via checkboxes. A search field appears for long lists. Changes are not applied until the user selects Apply. The trigger label after selection shows the item name when one is selected, and "2 selected", "3 selected", and so on when more than one is selected.

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** An open multi-select menu with grade checkboxes and an Apply button; after applying, the trigger collapses to read “Grade: 6th grade”. Source asset: `./assets/dropdown-select/multi-select.png`.

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** An open multi-select menu with two grades checked and an Apply button; after applying, the trigger collapses to read “Grade: 2 selected”. Source asset: `./assets/dropdown-select/multi-select-2.png`.

## States

These states apply primarily to the label-above variant, which has vertical space for context labels, helper text, and error messages. The inline variant may support some states depending on context, but the label-above variant is the default for stateful interactions.

### Required fields

Use "Required" as an inline label next to the field label instead of an asterisk. This is more accessible and explicit — users don’t need to find and interpret a legend.

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** A “Grade” dropdown with a “Required” label to the right of the field label instead of an asterisk. Source asset: `./assets/dropdown-select/state-context.png`.

### Helper text

Used for helpful description text that would otherwise be hidden in a placeholder. Helper text is persistent — it stays visible before and after the user makes a selection. Use it when the context genuinely aids the user’s decision.

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** A “Primary language” dropdown with persistent helper text explaining that languages marked with an asterisk are not fully quality-tested. Source asset: `./assets/dropdown-select/state-helper-text.png`.

### Error

If the user submits or selects Apply without selecting a required item, the dropdown gains a red border and displays an actionable error message below the field. The label also turns red. The error clears once a valid selection is made.

> **Historical figure 12 — source figure reference (only approved samples, if any, are linked below):** A “Grade” dropdown in its error state: red label, red border, and the message “Select at least one grade” below the field. Source asset: `./assets/dropdown-select/state-error.png`.

### Read-only

Displays the current value while explicitly preventing interaction. Unlike disabled, read-only maintains clear color contrast — the content is still meant to be read. Always include helper text explaining why the field is locked.

> **Historical figure 13 — source figure reference (only approved samples, if any, are linked below):** A read-only “Class” dropdown showing “Period 3, Precalculus” with a lock icon and the helper text “Only teachers can edit this”. Source asset: `./assets/dropdown-select/state-read-only.png`.

### Disabled

Used when a prerequisite action has not been fulfilled. The field is grayed out and non-interactive. Once the dependency is met, it no longer displays as disabled. Do not use disabled when read-only is more appropriate — disabled implies unavailability, not restriction.

> **Historical figure 14 — source figure reference (only approved samples, if any, are linked below):** A grayed-out, non-interactive “Grade” dropdown in its disabled state. Source asset: `./assets/dropdown-select/state-disabled.png`.

## Interaction

### In-menu search

Add a search field inside the menu when the list is long or when users are likely to know the specific item they need. Applies to both single-select and multi-select. Trigger conditions:

-   **Large data sets:** the list contains more than 10–15 items or requires significant scrolling.
-   **Known-item search:** users are likely to know the specific name of the item they’re looking for (e.g., a real lesson, supported course or available category).
-   **Alphabetical / categorical lists:** the list is long enough that manual scanning becomes inefficient.

> **Historical figure 15 — source figure reference (only approved samples, if any, are linked below):** An open “Select school(s)” menu with a “Search schools” field at the top above a scrollable, checkbox list of schools. Source asset: `./assets/dropdown-select/in-menu-search.png`.

### Multi-select requires apply

Checking or unchecking items does not apply until the user selects Apply. This prevents the data from re-filtering on every selection, which would be disorienting.

Dismissing the menu without applying — clicking outside it or pressing Escape — discards the pending changes and leaves the previous selection intact. Dismissal is the cancel path, so no separate Cancel button is needed.

> **Historical figure 16 — source figure reference (only approved samples, if any, are linked below):** A multi-select grade menu with two boxes checked and an Apply button, collapsing to a “Grade: 2 selected” trigger only after Apply is selected. Source asset: `./assets/dropdown-select/multi-select-apply.png`.

## Copy

### Label clarity and truncation

Option labels must be clear, concise, and immediately understandable, avoiding ambiguity, jargon, or excessive abbreviation. The label displayed in the closed dropdown must fit on a single line and truncate with an ellipsis (…) if necessary, to prevent line wrapping and maintain the component’s compact footprint.

> **Historical figure 17 — source figure reference (only approved samples, if any, are linked below):** Side-by-side comparison: a recommended dropdown truncating “12 grade advanced placeme…” on one line, versus a discouraged dropdown wrapping “12 grade advanced placement” onto two lines. Source asset: `./assets/dropdown-select/copy-truncation.png`.

### Logical ordering

Order options logically. This can mean arranging them alphabetically, numerically, by popularity, or by functional grouping, depending on what best supports the user’s scanning process.

> **Historical figure 18 — source figure reference (only approved samples, if any, are linked below):** Two menus showing ordering strategies: a status list ordered by functional grouping (To do, In progress, Complete) and a state list ordered alphabetically (Alabama, Alaska, Arizona). Source asset: `./assets/dropdown-select/copy-ordering.png`.

## HSK AI product application

### HSK AI selected values and mobile safety

- The HSK level or lesson choices must match the **actual available product and account state**. Do not show unsupported levels, fabricated exercise types or a default that silently changes stored progress.
- For a small fixed set of choices, preserve the original guidance to show options directly where space permits. On phones, long translated labels, Hanzi and pinyin must not become unreadable solely to satisfy a rigid desktop layout.
- Source illustrations are teaching references only. Keep the professional visual anatomy, option hierarchy and keyboard/focus behavior; use approved HSK AI brand icon/semantic roles and implement the appropriate anchored menu or mobile sheet for actual platform constraints, with at least 44 CSS px touch area on iPhone PWA and 48 dp on native Android. The current sheet visuals may be redesigned later.
- Keep single-select commits immediate, multi-select pending until Apply, and Cancel nondestructive. Required, disabled, read-only and error states retain distinct meanings and accessible explanations.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: copy-ordering.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/copy-ordering.png)

- [copy-ordering.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/copy-ordering.png) — exact source blob `7d5a25e3b481` (illustrated above)
- [copy-truncation.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/copy-truncation.png) — exact source blob `7c9fa2167755`
- [dropdown-select.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/dropdown-select.png) — exact source blob `e8b14fde21cb`
- [in-menu-search.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/in-menu-search.png) — exact source blob `7f56fa029a25`
- [label-above.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/label-above.png) — exact source blob `23c265ede998`
- [label-inline.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/label-inline.png) — exact source blob `724173d629c8`
- [multi-select-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/multi-select-2.png) — exact source blob `2992cbd51102`
- [multi-select-apply.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/multi-select-apply.png) — exact source blob `dc4b4d8d9d2a`
- [multi-select.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/multi-select.png) — exact source blob `f461f407e82f`
- [single-select.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/single-select.png) — exact source blob `f76bc77c9844`
- [state-context.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/state-context.png) — exact source blob `c9ecdcac69db`
- [state-disabled.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/state-disabled.png) — exact source blob `6471457f2441`
- [state-error.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/state-error.png) — exact source blob `92b156667713`
- [state-helper-text.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/state-helper-text.png) — exact source blob `40ad7d104904`
- [state-read-only.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/dropdown-select/state-read-only.png) — exact source blob `14a3203b64bb`
