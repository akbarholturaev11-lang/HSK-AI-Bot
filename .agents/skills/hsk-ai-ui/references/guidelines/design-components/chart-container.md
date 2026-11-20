> **HSK AI professional design guideline — portable review copy.** Current implementation is not implied. Source `__docs__/design-components/chart-container.mdx` (Git blob `48f5d439b29c5d70d9ee55f1effc8b8ffb58f8e2`); 4 historic figure references, 0 MDX demo blocks. Approved neutral example PNGs are linked below where available; excluded foreign screens and vendor runtime code were not transferred. The original prose remains an internal source-derived draft. Full professional prose is retained as an internal source-derived draft.

# Chart container

A chart container holds **one actual HSK AI data visualization**, a clear title, the essential scope, and any verified controls or timestamps. The container is a **documentation pattern**, not a mandatory third-party chart library or a claim that HSK AI currently implements every example.

## When to use

- One real [progress](progress-charts.md), [distribution](distribution-charts.md) or [trend](trend-charts.md) view needs contextual framing.
- A chart needs a specific title, verified values, optional time range and a few actual interactions.
- More than one distinct chart appears in the report: give each its own container to avoid competing interpretations.

Do **not** wrap an unrelated interactive table, a single KPI or a large multi-step form as a “chart container”. A [summary card](summary-cards.md), [data table](data-tables.md) or dedicated report section is clearer.

## Large and compact layouts

| Element | Larger report container | Compact mobile/dashboard container |
| --- | --- | --- |
| Section label | Names the topic, where appropriate. | Optional; avoid duplicate headings. |
| Chart title | States a grounded takeaway based on real data. | Names the metric/topic. |
| Description | Explains actual metric scope, period and denominator when necessary. | Only essential context. |
| Controls | A few real filters/actions with explicit scope. | Only if supported and still usable at phone width. |
| Chart | One meaningful visualization. | One simple chart that remains legible. |
| Footer | Actual last-updated/processing state when relevant. | Optional but required when stale data matters. |

On narrow screens, stack controls **below** the title when needed. Never force a borrowed desktop screenshot's top-right one-line layout, overlap the keyboard/bottom navigation or truncate important data.

## Controls

- Keep the **full professional anatomy and design guidance** for date picker, chart/table toggle, filter and download in the library. **Render and wire them in a real HSK AI screen only when implemented, authorized and supported by its actual backend.** Absence from today's app changes implementation status, not professional design quality.
- A chart/table switch must preserve the exact same records, permission scope, filters, denominator and window; it is not a second analytics query with unrelated data.
- Keep the controlled content obvious. A control in one container should not silently change unrelated charts above it.
- Use a dedicated report section when controls become complex. Refer to [Data reports](../design-patterns/data-reports.md) rather than copying a desktop toolbar.

## Empty, loading and error states

A loading container keeps known titles and filters stable and uses a shape-fitting skeleton for not-yet-known data. Distinguish actual zero from no observations, insufficient data, loading, failed query, stale snapshot or unavailable authorization.

On error, show an understandable message with real recovery, preserve unaffected independent charts and stale timestamp where applicable. Do not hide errors, required denominators or important scope beneath an optional two-line disclosure.

## Accessibility

- Use proper heading order, labelled values and real accessible names for controls.
- Describe the chart's meaning in text; never rely only on color or hover tooltip.
- Enable touch/keyboard access to supported data details.
- Keep HSK-related Hanzi, pinyin and localized language text legible under font scaling and both HSK AI themes.

## Interactive HSK AI documentation example

The following demonstration contains **fictional example values only**. It illustrates a real UI interaction (switching view, sorting, state, or range), **not** a functioning HSK AI analytics endpoint or a new production screen.

> **Illustrative demo:** TrendReferenceDemo (fictional example only; professional chart states and presentation are specified above).

## Restored professional reference examples

> **Source-only illustrations:** Every figure below originated in a different product's design guidelines. Preserve their professional layout and interaction principles; do not treat sample students, school data, scores, source colors or buttons as verified HSK AI functionality.

### Overview

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Historical chart-container overview showing a source data report, not real HSK AI analytics. Source asset: `./assets/chart-container/header.png`.

Overview: hierarchy of chart title, timeframe, controls and plot. Preserve the separation of data definition and presentation.

### Anatomy

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Source illustration of section heading outside a chart container and chart title inside. Source asset: `./assets/chart-container/heading-hierarchy.png`.

**Headings:** put the page/section H2 outside; a shorter chart title and optional description belong inside the container. Do not duplicate a headline in two places.

### Controls and comparison

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Original reference showing chart controls alongside the container title. Source asset: `./assets/chart-container/controls.png`.

**Control scope:** a chart-local dropdown applies to that chart; a page-wide date filter belongs above all affected results. Show the selected scope and avoid silent cross-chart filter drift.

### Alternative presentation

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Original reference showing chart and table view controls together. Source asset: `./assets/chart-container/view-toggle.png`.

**Alternative view:** when an authorized real chart has a table alternative, a clearly labeled toggle preserves the selected date range and filtered data. Do not fabricate unmeasured values in a table.

A professional report container has five layers: contextual heading, compact metric title, optional supporting explanation, **local controls with explicit scope**, and the visualization or its state. Choose a large layout when users need comparison or drill-down; use a compact layout only for a glanceable supported metric. In narrow phones move controls below the title rather than squeezing labels. A chart with no verified data needs an accurate empty/loading/error state, not a fabricated SVG.

## Restored professional decision contract

### Choose the right container

- Use a **large container** when readers need a comparison, a legend, data export, a date selector or additional explanation. Use a **compact container** only when one measured result can be understood at a glance.
- Do not use a chart container for a lone number (use a stat card), a table that needs substantial sorting or filtering (give the table its own section), or two unrelated visualizations (use separate containers).
- Keep at most a small set of local controls (approximately three). When controls need multiple rows or dominate the title, move the data view into its own section or screen; this is a layout heuristic, not a product feature.

### Exact anatomy and hierarchy

- The report section's **H2 is outside** a large container; its descriptive chart **H3 is inside**. A compact card uses the appropriate heading level within its real page outline; do not skip heading levels solely to change appearance.
- A useful insight title explains the **measured observation**, while a supporting description names the unit, population, date range and any important exclusion. Never state an unverified conclusion as fact.
- An optional legend belongs after the title/description and before the plot if direct series labels are insufficient. Show a last-successful-update timestamp when freshness matters; avoid fake live indicators.
- A table/chart view switch retains **the exact same scoped population, filters, denominator and date range**. Switching views must not silently change the statistic.
- Put page-wide controls above *all* results they govern; put chart-local controls in the specific container. On narrow phones, wrap controls below the title without truncating actions or violating the safe viewport.

### Operational and accessible states

- Empty or failed visualizations show a meaningful state **in the chart region**, not an empty graph or artificial zero. For a container-wide failure, keep unaffected report controls available; distinguish filtered-empty from no records.
- Export is offered only when permission and a working export route exist; export the same visible scope and indicate if the file uses a broader scope.
- Give icon-only controls explicit accessible action names including the chart topic (for example, “Show lesson completions as a table”); move focus appropriately after major state changes.
- Provide a text takeaway and an accessible data alternative. Neither a hover-only tooltip nor bar color can be the sole carrier of an essential value.

## Implementation boundary

This page removes inherited school-report screenshots, borrowed chart styling and dead source anchors. The HSK AI application and metrics pipeline remain unchanged.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: controls.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/chart-container/controls.png)

- [controls.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/chart-container/controls.png) — exact source blob `bfa77705a126` (illustrated above)
- [header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/chart-container/header.png) — exact source blob `46b39a10371c`
- [heading-hierarchy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/chart-container/heading-hierarchy.png) — exact source blob `b79f1e5885df`
- [view-toggle.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/chart-container/view-toggle.png) — exact source blob `24a4a881cc7b`
