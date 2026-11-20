> **HSK AI professional design guideline — portable review copy.** Source: `__docs__/design-components/inline-filter-button.mdx`, Git blob `e12248e82dc385f47aa7b0135b7b720cd50e2010`. 6 historic figure references and 0 MDX demo blocks; source images / vendor runtime code were not copied. Source prose remains an internal derivative draft pending rights and detailed visual parity review; this does not assert a live app feature.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Inline filter button. Source asset: `./assets/inline-filter-button/inline-filter-button.png`.

# Inline filter button

> **HSK AI application:** The source's School/Grade examples explain **optional filtering mechanics only**. In HSK AI these can correspond to actually available level, exercise-type or recorded activity criteria; do not add filters for unsupported states, and do not copy the desktop school filter bar.

*Component role: Additive filter control*

An opt-in filter control that lives in a filter bar. Starts unfiltered — all data shows. User adds a filter by clicking the inactive inline filter button. Always clearable with ×.

## Recommended: When to use

The choice to use an inline filter button is based on the need to allow users to optionally narrow data by a dimension without imposing a default. The filter starts inactive and data shows unfiltered until the user opts in.

| Use when | Rule | Example use |
| --- | --- | --- |
| Filtering is optional | All-time or unfiltered data is a valid and useful default | An existing lesson list that shows all available lessons until an optional exercise-type filter is applied |
| User owns the initial state | The product has no meaningful default to pre-apply | Filtering a recorded practice list by a supported HSK level when all available levels are initially shown |
| Multiple filters in a bar | Several opt-in filter comboboxes sit side by side in a filter bar, each independently addable and clearable | HSK level and exercise type as optional criteria on an applicable learning list |

## Avoid: When NOT to use

Avoid the filter combobox when a value is always required or when the control lives inside a form or modal.

| Don't use when | Recommended alternative | Rationale |
| --- | --- | --- |
| A default value is always applied | Dropdown | If the product pre-selects a value and it can't be cleared, use a dropdown |
| Inside a form or modal | Dropdown | The combobox is a filter bar affordance — it doesn't belong inside a form |
| Filtering by a time period | Date filter combobox | Use the date filter component — same opt-in pattern but purpose-built for temporal filtering |

## Variants

### Single-select

User selects one option. Selecting immediately applies and closes the menu — no Apply button. The filter combobox updates to the active state instantly.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Three states of a single-select inline filter button stacked vertically: `Inactive` shows a `Course` chip with a plus icon; `Open and selected` shows an open menu listing `Geometry 1`, `Algebra 1`, and a checked `Algebra 2`; `Filtered (active)` shows the chip reading `Course: Algebra 1` with a clear icon and a chevron.. Source asset: `./assets/inline-filter-button/variants-1.png`.

### Multi-select

User selects one or more options via checkboxes. A search field appears for long lists. Changes require Apply to confirm.

Trigger label after selection:

- 1 selected: shows the item name
- 2 or more: shows `2 selected`, `3 selected`, etc.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Three states of a multi-select inline filter button stacked vertically: `Inactive` shows a `Grade` chip with a plus icon; `Open and selected` shows a scrollable checkbox menu with `6th grade` and `7th grade` checked, `8th grade` unchecked, and an `Apply` button pinned below a separator; `Filtered (active)` shows the chip reading `School: 2 selected` with a clear icon and a chevron.. Source asset: `./assets/inline-filter-button/variants-2.png`.

## Interaction

### In-menu search

Follows the same rules as the Dropdown component. See [Dropdown documentation](dropdown-select.md).

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** An open `School` inline filter button with a `Search schools` field at the top of the menu, above a scrollable checkbox list of school names.. Source asset: `./assets/inline-filter-button/interaction-1.png`.

### Multi-select requires apply

Follows the same rules as the Dropdown component. See [Dropdown documentation](dropdown-select.md).

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** An open `Grade` inline filter button with `6th grade` checked, `7th grade` and `8th grade` unchecked, and an `Apply` button below a separator — the selection is not committed until Apply is pressed.. Source asset: `./assets/inline-filter-button/interaction-2.png`.

### Multiple filters in a bar

Multiple filter comboboxes sit side by side in a filter bar. Each is independent — clearing one does not affect others. The recommended maximum is 3 per bar. If more are needed, evaluate whether a More filters modal is more appropriate.

For active filters display behavior and "Clear all filters" logic, see the [Filter and sort pattern doc](../design-patterns/filter-and-sort.md).

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** A report page with a filter bar containing a `Last 30 days` date filter followed by three inline filter buttons — `School`, `Grade`, and `Subject` — highlighted together, above a `120 results` count.. Source asset: `./assets/inline-filter-button/interaction-3.png`.

## HSK AI product application

### HSK AI mobile usage

- Keep the original difference: a single choice takes effect immediately, while choosing several values requires an explicit Apply action. Cancel/dismiss must preserve the previously applied choices.
- On a narrow PWA/Android screen, do not force several filters onto one horizontal row. Use readable wrapping or the existing mobile selection sheet and preserve visible applied selections.
- These criteria are **examples**, not a mandate to add filtering to every vocabulary, exercise or reporting screen. A dependency between options must be backed by real product data.
- The result count must reconcile after each change. Clearing a filter never alters a learner's actual answers, study record or account data.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: inline-filter-button.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/inline-filter-button/inline-filter-button.png)

- [inline-filter-button.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/inline-filter-button/inline-filter-button.png) — exact source blob `97c6bde9230a` (illustrated above)
- [interaction-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/inline-filter-button/interaction-1.png) — exact source blob `b48c04571a81`
- [interaction-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/inline-filter-button/interaction-2.png) — exact source blob `d4e25ef4faef`
- [variants-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/inline-filter-button/variants-1.png) — exact source blob `346126e6514b`
- [variants-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/inline-filter-button/variants-2.png) — exact source blob `b17bdf51c3ab`
