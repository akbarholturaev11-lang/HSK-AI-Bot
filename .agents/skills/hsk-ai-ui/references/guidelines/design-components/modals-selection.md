> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/modals-selection.mdx`, Git blob `d7d346ac458c58d2d52157c2acfe302ae276a4fa`; 13 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Modals - selection. Source asset: `./assets/modals-selection/modals-selection.png`.

# Modals - selection

> **HSK AI scope:** The original screenshots demonstrate filtering structure, not the HSK AI app's colors, school categories or final appearance. Apply the original professional pending-vs-applied, reset, dependency, stable-control and accessibility rules with mobile sheet placement and only supported HSK AI categories.

*Component role: Complex filtering*

A secondary control center for less frequent, complex filters, keeping the current HSK AI learning or reporting screen uncluttered. Use it only for filters and data categories the product actually implements.

## Recommended: When to use

The choice to use the selection modal is determined by the need to provide access to extended filtering criteria that would otherwise overwhelm the horizontal real estate of the primary filter bar.

| Use when | Example use |
| --- | --- |
| Housing secondary filters used less frequently than primary anchors | Grouping extra available HSK level, lesson type or study-history criteria in the selection sheet. |
| The filtering interaction combines multiple input types that are too complex for the filter bar | Selecting a real exercise type may reveal a supported related subtype, if the underlying data has that relationship. |

## Avoid: When NOT to use

Avoid the selection modal when the filtering need is simple enough to be handled directly in the filter bar, or when a pre-selected default should always be visible to the user.

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| A filter needs to be pre-selected or always visible | Embedded filter dropdown | If a real date range or HSK level is already applied, that fact must be visible outside the selection sheet. |
| Only one additional filter is needed | Standard dropdown | If only one additional filter is needed, a simple dropdown in the filter bar is more efficient than a modal. |
| The user needs to search by keyword | Search field | Users expect search to be a persistent, high-level action in the primary UI rather than hidden in a modal. |

## States

### Default modal

All filters are secondary by default when the modal is first opened or currently applied. The modal displays all the available filter sections simultaneously.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** A “More filters” modal over a dimmed report showing all filter sections at once — Display options, Course, Subject, and Practice — with Reset filters and Apply filters in the footer. Source asset: `./assets/modals-selection/default-modal.png`.

## Placement

### Common placement

Open from a discoverable "More filters" action next to the relevant list or report. On phones, a horizontal desktop filter bar is not required.

The "More filters" button in the primary UI should display a numeric badge (e.g., "2") to indicate how many hidden filters are currently active.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** A filter bar with Last 30 days, School, and Grade filters followed by a “More filters” button at the end. Source asset: `./assets/modals-selection/common-placement.png`.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** A filter bar where the “More filters” button carries a “2” badge, with the two active hidden filters shown as chips below. Source asset: `./assets/modals-selection/filter-badge.png`.

### Internal layout

Group filters into clearly labeled sections using headings — e.g. "Display options," "Course," "Subject." This reduces cognitive load and helps users find related filters quickly.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** The selection modal with its filters grouped into labeled sections, the “Display options” section heading highlighted. Source asset: `./assets/modals-selection/internal-layout.png`.

### Footer actions

Keep Apply and Reset reachable in the pinned footer. On mobile, controls can stack or fit a row according to language length and screen width, with Apply the clear primary action. The footer must not hide behind the keyboard or safe area.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** The selection modal footer highlighted, with Reset filters anchored bottom-left and Apply filters bottom-right. Source asset: `./assets/modals-selection/footer-actions.png`.

## Interaction

When designing the content of the modal, refer to the specific documentation for components like [dropdowns](dropdown-select.md), [radio buttons](radio-button.md), [checkboxes](checkbox-group.md), and [toggles](toggle.md) to ensure input consistency. For backdrop behavior, sizing, and animations, refer to the [Modals documentation](modals.md).

### Applying changes

Nothing in this modal reaches the report until the user selects "Apply filters". Every control — dropdowns, checkboxes, toggles — holds its pending value inside the modal until then, so the user can set several filters at once without the report re-querying between each one.

Dismissing the modal with the X, the Escape key, or a click on the overlay discards pending changes and leaves the report unchanged. Filters are non-destructive and quick to redo, so dismissal does not warn — unlike a functional task modal, which must warn before discarding entered data.

Reopening the modal shows the filters currently applied to the report, not the pending state that was abandoned.

### Layout — category labels

On phones, labels can appear above their controls to keep text and touch targets usable. A separate label column is suitable only when the actual screen width supports it.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** The selection modal with a highlighted left column of category labels aligned against the filter controls on the right. Source asset: `./assets/modals-selection/category-labels.png`.

### Layout — exposed options

On phones, one readable column is the default. Use up to two columns only on sufficiently wide screens with short labels, without truncation or tiny touch targets.

Order options down the first column, then the second, so reading order matches list order. This is also the only arrangement where source order, visual order, and tab order agree.

A section never scrolls on its own. The modal body is the only scrolling region, and the footer is pinned — "Apply filters" stays reachable however long the content runs.

### Toggle behavior

Within the modal, toggles should be placed full-width and left-aligned, with the label on the left and the toggle aligned to the right.

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** A “Display options” section with full-width toggle rows, each label on the left and its toggle aligned to the right. Source asset: `./assets/modals-selection/toggle-behavior.png`.

### Dynamic content — adaptive controls

Filter choices are derived from the actual HSK AI data, so the list may vary by learner, level, supported exercise type or authorized reporting scope. When a list resolves to eight or fewer options, the dropdown is replaced by exposed checkboxes, following the [option-count rule](dropdown-select.md) used across the system.

The form is decided when the modal opens and holds until it closes. A control never changes shape while the user is in the modal, even if another selection narrows its options — a control that changes form mid-interaction moves a target the user is aiming at and casts doubt on selections already made.

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** A Course row shown as a “Select a course” dropdown while the option list is still long. Source asset: `./assets/modals-selection/adaptive-controls-1.png`.

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** The same Course row after the option list is reduced, now shown as exposed checkboxes: Algebra 1, Geometry, Algebra 2, and Trigonometry. Source asset: `./assets/modals-selection/adaptive-controls-2.png`.

### Dynamic content — parent/child logic

Support dependencies only where real data makes one criterion depend on another, such as a real exercise subtype filtered by exercise type.

The child control is not displayed until the parent holds a value. When the parent changes, the child keeps its value if that value is still available under the new parent, and is cleared if it is not. Never carry forward a child selection the user can no longer see — an orphaned value produces a filter state nothing in the interface explains. When the parent is cleared, or the new parent has no children, the child is removed along with any value it held.

The change happens in the modal, visibly, at the moment the parent changes — not silently on Apply.

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** A More filters modal with Practice set to “Placements” and no dependent control below it yet. Source asset: `./assets/modals-selection/parent-child-1.png`.

> **Historical figure 12 — source figure reference (only approved samples, if any, are linked below):** The same modal after the parent is set, with a dependent “Select a test” dropdown now revealed beneath Practice, both highlighted. Source asset: `./assets/modals-selection/parent-child-2.png`.

### Reset filters behavior

Selecting "Reset filters" returns every control in the modal to its default value — dropdowns, checkboxes, and any toggles set within the modal. It resets to defaults rather than clearing to empty: a toggle that ships on returns to on, not off.

The modal stays open and nothing reaches the report until the user selects "Apply filters". Reset is a change like any other made here, so it follows the same commit path — the user can see what the reset did, adjust from there, and dismiss without committing if they change their mind.

This is not the same action as Clear filters in the filter bar, which removes active filters from the report rather than returning controls to their defaults. Clear and reset are distinct verbs in this system: clear removes to empty, reset returns to a default. See [Clear filter](clear-filter.md).

> **Historical figure 13 — source figure reference (only approved samples, if any, are linked below):** The selection modal footer with the “Reset filters” button highlighted. Source asset: `./assets/modals-selection/reset-filters.png`.

## HSK AI mobile selection and data checks

- Choose a **professionally composed bottom sheet or compact modal** based on information density, control anatomy and available phone space; respect real iPhone/Android safe areas, keyboard, scrolling and actual primary task navigation. The current sheet's visual layout does not override the professional target.
- Actual examples are available HSK level, exercise type, date or recorded lesson status; don't add filters for untracked results, invented rewards or unsupported activity.
- A draft selection must not affect results until Apply is activated. Closing discards **only draft filter changes**, never completed lesson answers, account settings or payments.
- Reset returns controls to their defined defaults and stays pending until Apply. Clearing active filters is different and has its own behavior.
- Maintain the source's rules for stable control shape, real dependent options and removal of orphaned selections. Group counts must match the filtered authoritative records.
- The retained source diagrams are reference illustrations only; do not reproduce another app's teacher or school filter bars as HSK AI product screens.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: adaptive-controls-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/adaptive-controls-1.png)

- [adaptive-controls-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/adaptive-controls-1.png) — exact source blob `607186ecde80` (illustrated above)
- [adaptive-controls-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/adaptive-controls-2.png) — exact source blob `ede268495f78`
- [category-labels.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/category-labels.png) — exact source blob `2f4d31f73666`
- [common-placement.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/common-placement.png) — exact source blob `74f553b0cdb4`
- [default-modal.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/default-modal.png) — exact source blob `c9a9e7ccb9f7`
- [footer-actions.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/footer-actions.png) — exact source blob `3b67ce148a59`
- [internal-layout.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/internal-layout.png) — exact source blob `16fb5006e959`
- [modals-selection.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/modals-selection.png) — exact source blob `149824bdf5fa`
- [parent-child-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/parent-child-1.png) — exact source blob `f0019b767d6c`
- [parent-child-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/parent-child-2.png) — exact source blob `821cc47eb100`
- [reset-filters.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/reset-filters.png) — exact source blob `61b0999cdb0f`
- [toggle-behavior.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/modals-selection/toggle-behavior.png) — exact source blob `662cf3582754`
