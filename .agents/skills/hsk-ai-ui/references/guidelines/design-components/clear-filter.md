> **HSK AI professional design guideline — portable review copy.** Source: `__docs__/design-components/clear-filter.mdx`, Git blob `542669f4afa117a7a4f163f40278934d019a2cc6`. 4 historic figure references and 0 MDX demo blocks; source images / vendor runtime code were not copied. Source prose remains an internal derivative draft pending rights and detailed visual parity review; this does not assert a live app feature.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Decorative banner showing a “School: Addison Middle School” active filter with a remove (×) button next to a “Clear all filters” link, set over abstract orange, yellow, and blue shapes.. Source asset: `./assets/clear-filter/clear-filter.png`.

# Clear filter

> **HSK AI application:** Preserve the source's distinction between **clearing optional applied filters**, **clearing search text**, **sorting**, and **resetting a form**. The source school examples and artwork illustrate behavior only; they are not HSK AI UI or learning categories.

*Component role: State reset*

A tertiary button that removes every filter the user applied in a single action, regardless of how many are in use.

## Recommended: When to use

The choice to use a clear filters button is determined by the need to provide a fast escape hatch for complex queries or empty result states.

| Use when | Example use |
| --- | --- |
| A filter combination returns an empty state | Clearing optional exercise-type or level filters when a supported lesson or vocabulary list returns no matches. |
| Dismissing active filters individually would be time-intensive | Returning to the full supported list after applying several optional learning filters, including a multi-select. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| Clearing a control that can't be empty | Leave the control at its current value | Controls that always hold a value — the embedded Date dropdown defaulting to Last 30 days, for example — define the scope of the view rather than narrowing within it, so there is no empty state to clear them to and Clear filters never touches them. Don't attach a clear affordance to these, and don't revert them to a system default: the current value may be one the user deliberately set. This applies to the embedded Date dropdown, not the Date inline filter button, which the user introduces and which Clear filters does remove. |
| Resetting a data entry form | Individual field editing | Do not implement "Clear all" functionality on forms. While "Clear filters" is a helpful escape hatch for viewing data, a "Reset form" button leads to accidental data loss. To ensure a safe user experience, avoid any global action that wipes unsaved user input. |

## What Clear all filters resets

Clear all filters removes every filter the user applied. See the table below for which controls that includes.

| Control type | Cleared by Clear all filters? | Why |
| --- | --- | --- |
| Standard dropdown or inline filter button | Yes | Starts empty or inactive, so any value present is a user choice. Generates an active filter, and Clear all filters removes it — including every value in a multi-select, not just the first. |
| Date inline filter button | Yes | No date is pre-applied; the user introduces it, and it generates an active filter. Cleared along with the rest. |
| Toggle | Yes | Off is its empty state, so an on toggle is a narrowing the user applied. It generates no active filter, but the reset follows what the user constrained, not what appears as a chip. |
| Embedded filter dropdown (e.g. Date, defaulting to Last 30 days) | No | The product supplies the starting value and the control can't be cleared to empty. This is scope, not a filter — and reverting it would change a value the user may have deliberately set. |
| Segmented control | No | One segment is always selected, so there is no empty state to clear to. Switching views is scope, not narrowing. |
| Sort control | No | Sorting changes the order of results, not which results are shown. It narrows nothing, so there is nothing for the button to clear. |
| Search field | No | The query is authored text, not a selection. Clearing it would destroy input the user can't restore by re-picking, and the field clears in place on its own. |

Because the reset reaches past the chip row, the label says so — "Clear all filters," not "Clear filters." The "all" signals that narrowings without chips go too.

## States

### Hidden (inactive)

The button should not be visible if no filters are applied, preventing UI clutter.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** A report filter bar with a search field, a “Last 30 days” date filter, and inactive School, Grade, and More filters controls. No active filters are applied, so no Clear all filters button appears. The view shows 120 results.. Source asset: `./assets/clear-filter/states-hidden.png`.

### Default (active)

Appears as a [tertiary button](buttons.md) at the small size — `kind="tertiary"`, `size="small"` — once a filter is triggered.
Avoid using red or other high-caution colors. Clearing filters is an inconsequential action that does not delete data; use neutral styling to keep focus on primary actions.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** The same filter bar with School and Grades filters applied, shown as active School and Grades controls. Below the bar, an active filters row lists School: Addison Middle School, Grade: 7th grade, and Subject: Math, with the Clear filters button at the end of the row. The view shows 4 results.. Source asset: `./assets/clear-filter/states-default.png`.

## Interaction

Activating Clear filters removes all active filters at once and updates the results immediately. The action takes effect without a confirmation step — clearing filters changes what is displayed, never the underlying data, so there is nothing to lose and nothing to confirm.

### Focus

The button removes itself from the page as it acts: once the last active filter is gone, the button is hidden. This destroys the user's focus position, so focus must be moved deliberately rather than left to fall back to the top of the document. On activation, move focus to the results region, which should carry `tabindex="-1"` and an accessible name. This keeps a keyboard user moving toward the content they just asked to see, rather than dropping them back into the filter controls they have finished with.

### Announcement

Removing the filters changes the results without moving the user, which a screen reader user has no way to detect. Announce the outcome through the # results text.

### Layout stability

The button sits within the active filters row, which already appears and disappears with the filters themselves. It therefore introduces no layout shift beyond the row's own, and the row should reserve its height consistently so results below do not jump as filters are added and removed.

## Placement

Position the "Clear filters" button directly following the list of [active filters](active-filters.md).
It should sit between the filter bar (controls) and the data (results), providing a clear bridge between the two. For the full filtering pattern, see [Filter and sort](../design-patterns/filter-and-sort.md).

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** An active filters row — School: Addison Middle School, Grade: 7th grade, and Subject: Math, each removable — followed by the Clear filters button at the end of the row, sitting between the filter bar above and the results list below.. Source asset: `./assets/clear-filter/placement.png`.

## Copy

The label is always "Clear all filters" — sentence case, plural, no ending punctuation. Do not substitute "Reset", "Clear all", or "Clear".

## HSK AI product application

### HSK AI safety and mobile application

- Clearing filters changes **only which records are displayed**. It must not delete any vocabulary item, lesson result, progress, unsaved form input or account preference.
- A typed search stays intact after Clear all filters by the source rule; the search field has its own clear control. Default/required course scope, reporting period and sort selection also retain their established behavior.
- On HSK AI mobile screens, keep this secondary action close to the active filter labels, reachable above the keyboard/safe area, and return accessible focus to the results after the button disappears.
- After clearing, announce the accurate result count. If the list is truly empty or data is unavailable, do not invent items merely to fill the view.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: clear-filter.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/clear-filter/clear-filter.png)

- [clear-filter.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/clear-filter/clear-filter.png) — exact source blob `dd0ae64847ad` (illustrated above)
