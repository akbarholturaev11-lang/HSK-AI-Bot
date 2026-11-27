> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-patterns/filter-and-sort.mdx`, Git blob `2164bb9f71fe65617dfcb00e3647364002876b4e`; 13 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Filter and sort. Source asset: `./assets/filter-and-sort/filter-and-sort.png`.

# Filter and sort

> **HSK AI application:** The professional examples define the target **filter-bar composition, control hierarchy, placement and interaction states**, not school-specific product rules or mandatory Khan Academy branding. In HSK AI, use these rules for **already-supported** lesson, vocabulary, practice-history and authorized analytics lists only. The UI must remain usable on iPhone PWA and Android.

This guide defines how interactive components work together to manage large datasets, ensuring users can navigate content with minimal friction.

[Original source demonstration (not HSK AI interface)](https://www.figma.com/make/XJsbikH15NhiBV6s2Yi8wl/Finding--Organizing--and-Viewing-Prototype?p=f&t=YW51oGABw6Xv1kLY-0&fullscreen=1)

## Usage and purpose

| Component | Affordance category | Use case and purpose |
| --- | --- | --- |
| Search field | Finding | Locates specific items via text input; ideal for unpredictable datasets. |
| Dropdown/select | Organizing | Space-efficient method for sorting or choosing a single filter from a long list. Can appear as buttons that, when clicked, reveal a list of options (for example, a real HSK level or exercise type) to narrow data results. |
| Checkbox group | Organizing | Allows for multi-select filtering, letting users view several categories simultaneously within a list or dropdown. |
| Radio buttons | Organizing | Used for mutually exclusive filtering where only one option can be active at a time. |
| Toggle | Organizing | Binary on/off constraint on the dataset (for example, "Show completed lessons only," if that view exists). Generates no active filter, but counts toward Clear all filters. |
| More filters modal | Organizing | A centralized secondary view containing advanced or low-frequency filters that are not in the primary action bar. |
| Active filters | Organizing | Dynamic, removable elements that represent active filters. Clicking the "X" removes the specific parameter from the view. |
| Clear all filters | Organizing | A tertiary button that removes every filter the user applied. Does not revert controls to their system defaults, and does not reset sorting. |
| Segment control | Viewing | Best for switching between 2–5 related views of the same data, such as "Day / Week / Month". |
| Sort control | Organizing | Typically an icon-based button (e.g., arrows) used to quickly toggle between ascending and descending order. |
| Tabs | … | … |
| Pills | … | … |

## Logic framework: how they play together

Regardless of which components are selected for your specific use case, the system must follow these foundational rules:

- **Additive filtering (AND):** When a user selects a value from a Dropdown and then types in the Search Bar, the results must reflect both. The search is conducted within the already filtered subset.
- **Inclusive selection (OR):** Within a single component—specifically Checkboxes—selecting multiple items should expand the results (e.g., "Show me Blue OR Red items").
- **Cascading dependencies:** Primary filters (e.g., an actually available HSK course) dynamically "prune" dependent criteria (e.g., its available lessons) to show only valid, overlapping options. If a primary filter is changed, any now-invalid secondary selections are cleared to prevent "No Results" states. In the filter bar, a child filter is not displayed at all until its parent holds a value, and is removed when the parent is.
- **Global filter reset:** Provide a "Clear all filters" function as soon as the user applies an optional filter. This removes applied optional filter choices without manual deselection. A toggle counts even though it produces no chip. Typed search, non-clearable scope selections and sort order are retained, as specified in the Clear filter guideline.

### Experience flow: the discovery sequence

This section illustrates the logic framework in practice, transitioning from broad keyword discovery to granular category refinement. It demonstrates how the UI maintains data integrity through cascading logic while providing immediate visual feedback and reset options as users interact with the filter bar.

### Filter bar

The horizontal filter bar is located directly above the content list to provide immediate access to data refinement tools.
It can feature things like (and in this order) Search field for keyword queries, embedded dropdowns for high-priority + preset selections (e.g., Last 30 days), compact additive dropdowns for **actually supported** categories (for example, an existing HSK study level or lesson status), and for advanced segments, the More Filters button opens a comprehensive modal for less frequent criteria.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 1. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-1.png`.

### Search field

A search field allowing users to type keywords to find specific items within the dataset. When this view implements suggestions, typing may reveal supported matching lesson or vocabulary choices without changing the main result set. The main results update only after a suggestion is selected or the query is submitted, consistent with the search-field rule; unsupported autocomplete must not be implied as an existing HSK AI feature.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 2. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-2.png`.

### Embedded filter dropdown (single-select)

This variation is used for essential criteria that require a value to be active at all times, such as Date. Typically restricted to a single selection at a time to maintain a clear, focused data view. Because these are fundamental to the dataset, they remain visible in the filter bar as the primary anchors for the results displayed. Only use this for a verified necessary scope (for example, a time range or permitted course segment) where the real data model cannot safely display all records without a primary selection.
Use them sparingly (1–2 max) to avoid over-constraining the data and forcing a "Zero Results" state before discovery begins.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 3. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-3.png`.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 4. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-4.png`.

### Compact additive dropdown (single or multi-select)

This specific style of dropdown is designed for high-frequency use within the horizontal filter bar. It allows users to manage common data categories—such as HSK level or exercise type when these are supported—efficiently within a limited space.
Treat the source four-category upper bound as a generous wide-layout heuristic only where a larger viewport comfortably supports it; the inline-filter component recommends three visible filters per row. On HSK AI phones use fewer visible controls or the existing selection sheet when needed.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 5. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-5.png`.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 6. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-6.png`.

### Dependent filters (parent/child)

Some filters only make sense once another is set — selecting a supported HSK course before an available lesson subtype, for example.

In the filter bar, the child control is not shown until the parent holds a value. Removing or clearing the parent removes the child with it, along with any value it held and any active filter it produced. A child filter never appears on its own, and never outlives the parent that justified it.

The same rule applies inside the More filters modal — see [Modals - selection](../design-components/modals-selection.md).

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** A filter bar with Search, Last 30 days, School, and More filters controls. No School is selected, so no Teacher control appears. The view shows 40 results.. Source asset: `./assets/filter-and-sort/dependent-filters-1.png`.

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** The same filter bar with School set to Addison Middle School, which reveals a dependent Teacher dropdown beside it. A School active filter and the Clear all filters button appear below. The view shows 4 results.. Source asset: `./assets/filter-and-sort/dependent-filters-2.png`.

### More filters modal

The More filters component serves as a secondary control center for complex or less frequent filtering needs, ensuring the primary interface remains uncluttered. The button carries a numeric badge showing how many filters inside are active. For a toggle applied in the modal, the badge is the only indication it is on, since toggles produce no chip.

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 7. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-7.png`.

### Active filters

Active filters are displayed directly below the filter bar to provide transparent feedback on the current dataset.

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 8. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-8.png`.

### Clear all filters

A "Clear all filters" button appears as soon as the user applies a filter — including a toggle, which produces no chip. Users can return to a neutral state instantly without manual deselection, regardless of how many components are in use. See [Clear filter](../design-components/clear-filter.md) for which controls it removes and which it leaves alone.

> **Historical figure 12 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 9. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-9.png`.

> **Historical figure 13 — source figure reference (only approved samples, if any, are linked below):** Logic framework: how they play together 10. Source asset: `./assets/filter-and-sort/logic-framework-how-they-play-together-10.png`.

## HSK AI product application

### HSK AI application and mobile behavior

- Search for Chinese learning content only within the records and search modes the real app actually supports. Do not assert that searching by Hanzi, pinyin or translation is implemented unless it has been verified for that view.
- Keep **AND** between distinct filters/search, **OR** among chosen values inside one multi-select, and remove invalid child selections when a parent changes. Do not invent filtering dependencies absent from the stored data.
- Retain the difference between clearing applied optional filters, resetting to system defaults, clearing typed search, and changing sort order. These actions have different meanings and must not erase lesson answers, saved work or account settings.
- On narrow mobile screens, controls may wrap or move into the existing bottom-sheet pattern; source desktop screenshots and the external prototype demonstrate behavior only and must not dictate HSK AI page geometry.
- The visible count, listed records and any authorized report total must agree after filtering and sorting. Keep empty, loading, error and partially tracked states distinct; no invented results or unsupported sorting.
