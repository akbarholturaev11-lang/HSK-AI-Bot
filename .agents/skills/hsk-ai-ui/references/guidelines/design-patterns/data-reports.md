> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-patterns/data-reports.mdx`, Git blob `270a4b3fe4422de9e6f273c312844ce84431f748`; 9 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# HSK AI data reports

Reports help a learner understand **their own recorded Chinese-study progress**, or help an **authorized administrator** inspect verified HSK AI product activity. Those are different audiences. These guidelines define professional report interaction and data integrity; they do not claim every proposed chart or control currently exists in the PWA or Android application.

## Decide whether the result needs a number, chart or table

| Choose | When | HSK AI application |
| --- | --- | --- |
| [Summary card](../design-components/summary-cards.md) | One verified number or comparison tells the story | An actual completed-lessons count with its scope and time range |
| [Progress chart](../design-components/progress-charts.md) | A current value can be compared with a **real defined goal** | Progress toward an actual supported study goal |
| [Distribution chart](../design-components/distribution-charts.md) | Readers need the spread across meaningful non-overlapping groups | Recorded attempts/results grouped by valid existing ranges |
| [Trend chart](../design-components/trend-charts.md) | Several comparable periods show direction of change | A recorded learner metric tracked over valid date windows |
| [Data table](../design-components/data-tables.md) | Readers need exact records, labels or action on one record | Individual lesson records, dates or verified scores |

Do not chart one lonely value or invent a heat map, grading scale, metric, leaderboard or peer comparison just because the source library demonstrates one.

## Useful reporting rules

1. A chart answers **one question**; its title communicates the relevant supported takeaway, not merely “Chart”.
2. Give a meaningful **metric definition, denominator, scope, unit and period** for counts and percentages. Do not compare course versions or platforms with different event definitions without stating the limitation.
3. Show only the data required for the point. When exact values are needed, use a table; when a chart becomes unreadable on a phone, choose a simpler presentation.
4. Do not make the reader decode more than a few unexplained series or colors. All essential information must also be available without color and to assistive technology.
5. A report must not turn missing data into zero, aggregate duplicate analytics events as real activity or claim an unverified server result is complete.
6. Distinguish an HSK level, a recorded score, a completed lesson, an attempt, a streak, a paid entitlement and an AI Voice use. They do **not** measure the same thing.

## Showing genuine growth

Growth requires the same defined measure across comparable periods.

- To show how a population spreads across two valid periods, use a distribution comparison; keep categories and their thresholds consistent.
- To show a metric across **three or more** comparable periods, use a trend, leaving gaps for unavailable data instead of inventing zeroes.
- To identify a particular learner-owned result or authorized individual record, use a table only where the viewer is permitted to access it.
- State exactly which verified records appear **in both** compared periods and how many are excluded. Do not imply results for people or dates that were not observed.
- An overall average can conceal individual differences. Where authorized and actually tracked, show underlying denominators and meaningful variation.
- “Compared to” controls should update **all** dependent growth cards, graphs, tables and denominators together while leaving unrelated current-state metrics unchanged.

A learner account cannot see other users' personal results just because an old analytics example grouped students. An admin must have explicit authorization and appropriate privacy controls.

## Report layouts

### Compact container

Use one bounded container for a small chart, succinct title, real date or view controls and its data. On a narrow device, keep headings and values visible rather than reproducing a wide desktop report.

### Dedicated section or page

Use a dedicated area when controls and records no longer fit within one container. Arrange summary first, then focused containers, then the detail table. A control should affect only the records in its clearly communicated scope. If a filter is global, explain it clearly and keep the current selection visible.

### Filter, search and sort

- Show only filters and search methods that exist for the current HSK AI data and viewer permission.
- Apply `Clear filters` only to the **optional applied filters**: preserve search text, required scope and sort order unless the actual control explicitly states otherwise.
- Never fabricate “School”, “District”, “Grade” or classroom selectors for the learner interface.
- On small screens use the established HSK AI picker/sheet patterns, safe areas and accessible touch targets.

## Empty, loading and error states

### No records yet

Distinguish **not configured**, **not yet recorded**, **filtered to none**, **not enough observations**, **processing**, **not authorized** and **failed to load**. They are not equivalent.

- Explain what is missing without promising data that tracking cannot provide.
- Keep useful context and controls available.
- Offer a next action only when the user can actually fix the cause from that screen.
- Do not mandate another product's “No report data” graphic or account-roster synchronization.

### Empty-state placement and copy anatomy

Empty states should retain the **known context** and replace only the unavailable data. This keeps the source design's useful container-versus-page distinction while removing its mandated school illustration and roster actions.

| Report scope | Preserve | Replace or hide | Action |
| --- | --- | --- | --- |
| One empty chart, other charts valid | Section heading and any date/scope control that could change the result | That chart and its data-only controls, such as a chart/table toggle or download | A local action only if this screen can solve the actual cause |
| All report sections empty for the same verified reason | Report title, explanation and relevant global scope | Repeated empty cards that add no information | One well-scoped primary action, only when genuinely available |
| Dedicated list/table with no records | Page title, filters/search and truthful scope | Data rows; disable export or row actions that require records | An appropriate setup or retry action only if its precondition exists |
| Valid records excluded by filters | Applied filter controls and current query | Matching rows/marks only | Clear **optional** filters without erasing unrelated search or mandatory restrictions |

**Copy structure:** (1) a concise sentence-case headline naming what is missing, (2) one localized sentence explaining the *verified* reason or next condition, and (3) an optional, short verb-first action that actually works. Use “yet” only when data is genuinely expected; never promise an event, lesson, payment or analytics record that HSK AI cannot measure. Do not render a success or celebratory character state for an empty report.

### Filtered to nothing

Keep the relevant active filters visible. Offer a real `Clear filters` action only if it resets the optional filters; do not silently erase an entered query or mandatory account/period scope.

### Loading

Keep known labels and structure visible. A shape-matching skeleton may stand in for **data**, not for already known headings or action labels. Never render fictitious example metrics as if real values were loading.

### Error and retry

When loading fails, distinguish a **whole-page failure**, an **isolated chart failure**, and a **refresh failure with a valid earlier snapshot**. Keep earlier valid data when appropriate and visibly label its timestamp. Provide Retry only if a real retry exists. Preserve ownership protection on logout/account switches and make status changes accessible.

Do not hide critical error details behind the optional two-line chevron pattern. The user and an authorized admin require recoverable status and honest diagnostics, not a falsely reassuring success toast.

### Failure scope, previous data and permission

| Verified state | What stays visible | What changes |
| --- | --- | --- |
| Initial full-page load failed | Title, explanation, filters already known locally | One accessible failure message in place of data and a working retry control if available |
| One chart/container failed | All unrelated valid charts, failed section heading and its relevant controls | A localized, accessible error inside only that container |
| Refresh failed with an earlier authorized snapshot | Previously verified values **with their real timestamp** | One prominent update-failed notice; do not present the old values as current |
| Permission was removed or the account changed | Non-sensitive page structure and safe navigation only | Clear protected data and cross-account cached previews; do not show previous user's totals |
| Data is partial or still processing | Verified recorded subset, known definitions and period | Explain coverage limitations, do not turn missing events into zero or a complete total |

Retry must not destroy the user's search, optional filters, input or previously loaded authorized data. Screen readers must be informed of a newly surfaced error. A permanently failing retry needs a safe alternative such as a later retry or appropriate support path; do not invent an escalation action that is not present in the app.

### Incomplete or insufficient data

- A single observation does not justify a trend; a very small group may read better as a number or table.
- Do not silently turn missing Android/PWA events into “0”.
- Separate processing, incomplete sampling, duplicate detection, and current-versus-stale snapshots.
- Verify chart counts reconcile with filtered detail records and the displayed denominator.

## HSK AI presentation and accessibility

- Readable Hanzi, pinyin, localized lesson meaning and HSK course labels must remain accurate in tables, captions and related action labels.
- Use HSK AI's actual semantic light/dark colors, not external report screenshots, source score thresholds or school-theme palettes.
- Mobile screen, keyboard, bottom navigation, dynamic text and reduced-motion behavior take priority over fixed desktop screenshots.
- Provide descriptive headings, understandable counts/units and keyboard/screen reader equivalents for every chart. Never rely on color alone.
- Optional lengthy **secondary descriptions** may collapse to **at most two fully visible lines** with only a top-right ⌄/⌃ control, but charts, denominators, time ranges, errors, permissions and essential facts must remain visible.

## Interactive reporting-state example

This **fictional** demo distinguishes empty, filtered, stale and error states without implying live HSK AI analytics. A verified backend and access scope are mandatory in actual app reports.

> **Illustrative demo:** ReportStateReferenceDemo (fictional example; professional states remain documented in the guideline).

## Restored professional source examples

> **Historical education-product diagrams only.** These examples preserve valuable interaction, composition and state patterns, not HSK AI's actual screens, roles, artwork, data or feature inventory. See the HSK AI-specific rules above before making a production design decision.

### Example 1: header

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Original report structure with source metrics; not real HSK AI analytics. Source asset: `./assets/data-reports/header.png`.

A report begins with a purpose, scope, heading and verified current range; primary controls are not copied from another product.

### Example 2: own section

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Source example of a dedicated report section and filters; classroom data are illustrative only. Source asset: `./assets/data-reports/own-section.png`.

Give a dataset its own page or section when it needs many filters, search, sort or wide tables; place controls above the data they affect.

### Example 3: empty container

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Original empty chart-container pattern. Source asset: `./assets/data-reports/empty-container.png`.

When a chart alone has no records, retain its title and applicable controls while replacing only the visualization with specific neutral copy.

### Example 4: empty page

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Original no-records report-page pattern. Source asset: `./assets/data-reports/empty-page.png`.

For a totally empty report, keep page context and date/filter scope; distinguish no captured records from not authorized.

### Example 5: filtered container

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Original filtered empty container reference. Source asset: `./assets/data-reports/filtered-container.png`.

Show which filters exclude records. A local no-match state should guide the user to adjust that scope, not imply the backend has no data.

### Example 6: filtered page

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** Original filtered empty report reference with reset action. Source asset: `./assets/data-reports/filtered-page.png`.

Maintain applied filters and a legitimate clear-filters action without resetting unrelated search/sort unless the user chooses to.

### Example 7: error page load

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** Source full-report loading failure example. Source asset: `./assets/data-reports/error-page-load.png`.

If initial loading failed, do not display invented zero data; offer a real recovery action and preserve the user's filter choices.

### Example 8: error page update

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** Source report refresh failure with previous data retained. Source asset: `./assets/data-reports/error-page-update.png`.

If an update fails but older verified results remain, identify them as stale and retain them only where authorized; never present them as newly refreshed.

### Example 9: error container

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** Source error isolated to one chart container. Source asset: `./assets/data-reports/error-container.png`.

Failure of one card/chart should not destroy other unrelated loaded data. Give the faulty region its own accessible error notice.

### Professional state hierarchy

**No records** means successful fetch and empty authorized scope. **Filtered to none** means available records may exist but not match selected criteria. **Not enough data** means a chart comparison cannot yet be supported. **No permission** is different from either; never reveal protected totals. **Processing/partial coverage** must name its actual verified data status rather than display a false final total.

Report-level filters apply consistently to all included metrics; chart-local filters must be visibly scoped. Avoid double-counting duplicated events, mixing user- and admin-level identities, or comparing non-audited platform attribution with fully audited totals. On a phone, a large table can need a different layout, but must preserve actual record and filter semantics. Keep chart/table accessible data alternatives and enough width for Hanzi, pinyin and localized date formats.

## Restored report composition and comparison rules

### Page order and control scope

- Structure the report as **title and scope → key verified figures → supporting distribution/progress/trend → exact authorized records and actions**. Reorder only to match the reader's actual question; do not copy a desktop school dashboard into the learner phone UI.
- A control positioned **above multiple components** changes all those components coherently. A filter inside one chart changes only that chart. Display the chosen period/scope and do not leave a summary card on a different baseline from its detail table without explanation.
- Use a **dedicated section or page** when the data requires many controls, a complex table, or sustained comparison. An isolated chart container is appropriate for one simple result.

### Truthful growth

- Compare the **same defined measurement**, comparable scope, equivalent time period, applicable version and denominator. For multiple time windows, make the earlier-period selector explicit only where such comparisons are implemented.
- If only a subset of learners or events appears in both periods, state the matched population and excluded counts. A shift in group composition is not automatically improvement by the same learner.
- Lead with an actionable validated conclusion, not a decorative chart. A raw point difference alone may be meaningless if course definitions, event capture or data freshness changed.

### Empty, error and permission placement

- **No records ever:** explain that the scoped entity has not produced records and show the next genuine learning step. **Filtered to nothing:** keep filters and scope visible and offer to clear only the added filter constraints.
- **Container failure:** preserve unaffected cards and controls; explain which chart failed. **Full-page failure:** reserve page-level treatment for a genuinely unavailable report, not one failed metric.
- **Update failure with previous data:** label that data **last successfully updated**, not current; allow a safe retry without generating duplicate analytics events.
- **Partial or processing data:** show which period/source is incomplete. **Not enough data:** explain the actual minimum or calculation limitation only where the backend enforces one.
- **No access:** state the permission boundary and offer an appropriate existing route without leaking record contents. **Too much data:** paginate or narrow scope rather than silently dropping records.
- Use clear, localized, specific copy stating what happened and which safe action is available; no invented successful export, save, analytics freshness or server recovery.

### Mobile and accessibility

- Preserve safe areas, focus order, 4-unit spacing logic and a readable hierarchy. A compact chart must never force horizontal page overflow or obscure required lessons in favor of analytics.
- Provide text equivalents for numbers and charts, keyboard/touch access for supported interactions and clear status for loading, errors and stale results.

## Implementation boundary

All report actions and analytics must be verified against the current HSK AI source before use. This page deliberately excludes foreign school/district workflows, screenshots and score thresholds. It is a design document, not a change to product data collection, authorization, frontend code or a report endpoint.
