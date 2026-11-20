> **HSK AI professional design guideline — portable review copy.** Source: `__docs__/design-components/data-tables.mdx`, Git blob `aad03dea79633750d16f339330770cd5cb36a33f`. 3 historic figure references and 0 MDX demo blocks; source images / vendor runtime code were not copied. Source prose remains an internal derivative draft pending rights and detailed visual parity review; this does not assert a live app feature.

# Data tables

A data table is appropriate when a learner or authorized admin needs **exact verified records** rather than a chart's approximate visual pattern. HSK AI records may include supported lesson names, completion dates, correctly defined scores or review status, but only where those fields actually exist and that viewer is entitled to see them.

## When to use

- Individual rows, exact values, sorting or filtering are needed to answer the user's question.
- A small dataset would not benefit from a chart.
- The user needs to inspect an actual event, lesson, word or authorized metric entry.
- Data can be provided in a structured, accessible layout that fits the current platform.

Use a [summary card](summary-cards.md) for one fact, and a chart only when shape, spread or trends matter more than individual rows.

## Anatomy

| Part | Rule |
| --- | --- |
| Table title | Name what the records represent and their actual scope. |
| Column headings | Concise, unambiguous, localized and semantically marked as headers. |
| Rows | One logical record per row, linked to its legitimate HSK AI owner/scope. |
| Values | Precise unit, date/time, metric or learning-content identity. Avoid blank meaning. |
| Sorting | Describe the sorted field and direction. Default to a meaningful stable order such as lesson sequence, time or verified score where available. |
| Filtering | Only real optional filters; show the current scope and keep required account/HSK-level restrictions. |
| Row actions | Only actual permitted actions with accessible names; never expose someone else's record to the learner. |
| Pagination | Actual backend paging, not a fabricated count or an endless spinner. |

## HSK learning content

- Keep the real **Hanzi**, correctly marked **pinyin**, and localized meaning when that field is actually part of the record. A word title is not a generic teacher or class label.
- Do not alter or truncate the only identifier used to distinguish two words or lessons. Long optional supplementary details may use the approved top-right ⌄/⌃ two-line disclosure, but **essential learning values must remain visible**.
- Distinguish an exercise attempt from a completed lesson, a progress record, a correct answer and a Pro purchase; do not conflate them in one status column.
- No grade/classroom/teacher roster columns are prescribed here. The data model must come from the actual HSK AI feature.

## Sort, filter and count integrity

1. Keep the number of displayed or filtered rows consistent with any accompanying chart and summary count.
2. Sorting must be stable for equal values and preserve the user's current filter/permission scope.
3. A missing result is different from a measured zero; an incomplete record must not silently become a passing score.
4. Explain the real denominator for percentages and the time zone/date range for dated values.
5. Never apply source-school score thresholds or lesson-completion rules without inspecting HSK AI's actual scoring contract.
6. Where a table offers tabs or summary views, each tab's count and list must be calculated from the **same verified records**.
7. Do not insert fictional sample student records or unauthorized individual analytics to fill a design mockup.

## In-cell information and row controls

A cell must remain understandable when separated from color, chart decoration or surrounding rows. This preserves the source system's useful distinction between **exact values, in-cell visuals, status flags, and per-row actions**, without importing its school records or score rules.

| Cell content | Professional rule | HSK AI constraint |
| --- | --- | --- |
| Missing value | Use a localized em dash or explicit “Not recorded”; never silently substitute zero. | Explain whether an observation is absent, not applicable, still processing or unavailable because of permission. |
| Progress visualization | Show an exact readable value such as `12/20` alongside the bar; use a real non-zero denominator and accessible text. | The numerator, denominator and completion meaning must come from the same verified lesson/goal source. |
| Status badge | Pair a compact badge with understandable text; hue alone is insufficient. | Keep correct/incorrect learning feedback separate from upload, network, payment and destructive errors. |
| Action-required flag | Name what happened and the appropriate severity, not just a count or colored symbol. | Use only genuinely recorded recoverable conditions; do not create school-style overdue or “needs help” classifications. |
| Row action | Put genuine record-specific actions together at the row's trailing edge if more than one is necessary. | Announce the target in its accessible label, e.g. “Actions for [record]”; do not imply unsupported edit/export/delete controls. |

- **Keep flags sparse:** where two verified, independently meaningful flags coexist, order the most important first; use a more detailed record view rather than stacking many badges. The upstream two-flag example is a readability reference, not a new HSK AI severity API.
- **Align by data type:** text identifiers follow the reading direction, comparable numbers align on the numeric edge, and dates/times use the selected locale and declared time zone. Keep a stable column meaning within one table.
- **Bulk selection is conditional:** add selection checkboxes only if authorized bulk actions exist. Announce each row's identity, show the selected count and available actions together, and define what selection does when filtering or paging changes.
- **Long datasets:** use genuine server paging or validated virtualization with stable identifiers, sortable scope, selection and totals. The original desktop suggestion of 50 rows is not a universal mobile HSK AI limit.
- **Navigation:** real tab groups need the appropriate keyboard interaction and selected-state announcement. A table header should use `scope="col"` or the native equivalent; decorative mini-bars never replace an exact readable value.

## Mobile and accessibility

- Use actual PWA/Android layouts, not a forced desktop six-column table. Prefer a compact list/stacked row where that preserves meaning better.
- Label controls, column headers and any sort direction for screen readers. Keyboard and touch interactions must remain usable.
- Do not use color alone for correct/incorrect/processing states; keep text and verified status visible.
- Preserve font scaling, Chinese strokes, pinyin tone marks and Cyrillic/Uzbek/Tajik labels without clipping.
- Keep horizontal scrolling deliberate and discoverable if a dense admin table truly requires it; never hide a key action off-screen without an accessible alternative.

## States

Loading keeps known labels/header structure stable without fake data. Empty and filtered-to-none states explain the actual cause. A failed refresh may leave a previous valid snapshot with a timestamp and retry, but authorization failures must clear protected content.

Refer to [HSK AI data reports](../design-patterns/data-reports.md) for shared empty, retry, filtering, data-integrity and access rules.

## Interactive HSK AI documentation example

The following demonstration contains **fictional example values only**. It illustrates a real UI interaction (switching view, sorting, state, or range), **not** a functioning HSK AI analytics endpoint or a new production screen.

> **Illustrative demo:** TableReferenceDemo (fictional example; professional data/visual states are documented in this guideline).

## Restored professional reference examples

> **Source-only illustrations:** Every figure below originated in a different product's design guidelines. Preserve their professional layout and interaction principles; do not treat sample students, school data, scores, source colors or buttons as verified HSK AI functionality.

### Overview

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Source illustration showing a dense data table, not actual HSK AI student records. Source asset: `./assets/data-tables/header.png`.

Use a table for comparable structured records with stable column meanings. It is not a universal replacement for mobile lesson cards.

### Anatomy

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Original table example with short headings and name-first structure; sample school data are not HSK AI content. Source asset: `./assets/data-tables/basic-table.png`.

**Columns:** place the record identifier first, use concise sentence-case headers and correct text/numeric/date alignment. Numeric values should usually align on the end edge; dates must follow selected locale.

### Controls and comparison

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Original table with summary tabs; its school/classroom categories are illustrative only. Source asset: `./assets/data-tables/summary-tabs.png`.

**Tabs:** totals and scoped categories must come from the same verified query or explicitly different scopes. Switching tabs does not change the identity/authorization of the underlying data.

**Detailed cell guidance:** a missing number is not zero; use a localized dash or “not recorded” explanation. A status flag should link to a real verified status and be understandable without color. Sorting must compare actual values rather than localized strings, and the visual sort indicator and screen-reader announcement must match. Avoid a full grid and thick separators if restrained row lines are sufficient. For long tables preserve column headers, pagination/virtualization semantics, keyboard navigation and a compact mobile strategy; never hide an essential HSK character or translation behind a clipped cell.

## Restored table decision and interaction contract

### Selection, ordering and exact records

- Use a table when a reader must locate **individual authorized records**, compare exact values or perform a row-specific action. Use a stat card for a single headline and a chart for a broad pattern; a table must not be the default answer to every report.
- A **basic table** has stable column headers, clearly defined row keys and a documented default sort. A **summary-tab variant** is useful only when actual non-overlapping statuses or categories exist; tab totals must reconcile to the scoped dataset, and selection must announce which set is visible.
- Use precise column nouns, short sentence-case headers and a readable Hanzi/pinyin/meaning hierarchy when vocabulary is the subject. Numeric columns align consistently; date/time values show applicable locale and time zone.
- Show a real **0** for an observed zero, an em dash plus explanation for absent data, and distinct states for processing, unavailable, unauthorized and failed values. A missing score is not a zero score.
- Status flags are concise **icon-and-label** information, not color-only signals. The server must actually support the status. A progress bar inside a row must have a verified target, correct units and a text equivalent.

### Actions, density and navigation

- Sorting controls must indicate direction, preserve the active filter scope and use stable tie-breaking so rows do not jump unpredictably. A sorted numeric field must be sorted numerically, not as formatted strings.
- Show a **bulk-selection checkbox column only when authorized bulk actions exist**. Explain the selected count, clear selection on an identity/scope change and confirm destructive operations explicitly.
- Row-level actions apply to that exact stable record; do not imply “open details” if there is no verified route. If row click and inner buttons coexist, avoid nested interactive targets.
- On wide reporting surfaces, paginate or virtualize long tables; the original source's approximately 50-row-per-page guideline is a performance heuristic, **not** a guaranteed HSK AI product limit.
- On mobile, prefer a semantic stacked record list or a carefully disclosed horizontally scrollable data region over squashing Hanzi, numeric values and controls into illegible columns. Preserve column meaning and keyboard/screen-reader labels.

### Empty and error fidelity

- An unfiltered zero-result table retains context and offers the next relevant action. A filtered-empty table retains the applied filters and clear-filter control; explain “No matching records” rather than “No data exists.”
- Loading, partial aggregates and export results must share the **same authoritative population, period and counting method**. Reject duplicate-event totals and the accidental merging of Android and PWA event records when the same event ID represents one action.
- Learners can only inspect their own records. Authorized admin views must enforce permission before rendering values or exports, and must not leak prior-user rows after account switching.

## Implementation boundary

This is HSK AI guidance, not a schema migration or a promise that table sorting, pagination and exporting have shipped. It intentionally removes the source's teacher/grade/class screenshots, classroom record policy and school score examples.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: basic-table.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/data-tables/basic-table.png)

- [basic-table.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/data-tables/basic-table.png) — exact source blob `9826e9506e8a` (illustrated above)
