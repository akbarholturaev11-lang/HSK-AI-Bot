> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/trend-charts.mdx`, Git blob `2522b1d65b83f794b14b137b269da5b9f8efa0b5`; 2 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# Trend charts

*Component role: Verified change over time*

Trend charts answer **“How has this actual HSK AI measure changed over time?”** Use them only when comparable, verified data exists for multiple meaningful periods, with explicit units, scope and access. This page does not introduce a new assessment, learner benchmark, score system or API.

## When to use

- A tracked learner or authorized admin metric has **three or more** comparable observed time points and their direction matters.
- You need to compare a consistent learning activity or progress measure across date windows.
- A genuine learning target/reference line exists in the current system and is mathematically comparable with the series.
- An authorized viewer has permission for every data series being displayed.

## When NOT to use

- **One value** → summary card.
- **Exactly two values with no ongoing history** → a clear numerical difference with named periods may be easier to read than a two-point line.
- **Categories without chronological order** → distribution or grouped bars, not a line.
- **Missing, stale or mixed-definition observations** → explain the limitation; do not interpolate fictional activity or plot missing as zero.

## Anatomy

| Part | Rule |
| --- | --- |
| Heading | Name the actually recorded metric and the meaningful period. |
| Title | State a grounded, accurate change, not an invented fixed point gain. |
| Time axis | Chronological order. Space dates by elapsed time when the intervals differ; label units/time zone where relevant. |
| Value axis | Actual metric and unit, legible scale. A trend axis need not always start at zero, but must not exaggerate small differences. |
| Line and points | Use a clearly distinguishable theme role; label meaningful points where possible. |
| Missing window | Leave it missing and identified, not connected as a confirmed zero or the previous value. |
| Legend | Only if several truly compatible series exist, with text as well as color. |
| Date/filter controls | Control only their documented scope and update connected cards/denominators consistently. |

See [Chart container](chart-container.md) and [Data visualization](../design-foundations/data-visualization.md) for generic semantics, text summaries and visual hierarchy.

## Time and values

1. Plot only dates/windows whose records the current HSK AI system actually contains.
2. Real dates with irregular spacing must use a date-proportional axis or communicate unequal spacing. Named but non-equidistant periods must not silently appear equally spaced.
3. Keep a meaningful gap for unavailable periods; do not present a missing Android or PWA event as `0`.
4. State whether a value is a count, percentage, score, completion rate, verified streak, or other supported metric. They do not share one scale or denominator.
5. When an authorized viewer changes the reporting period, the title, line, dates, summary and denominator must agree.
6. Do not mix incompatible HSK course versions, owner accounts or event definitions into a trend without a disclosed and validated reconciliation.
7. A baseline or goal line requires an actual configured benchmark/target, not a fabricated school average.

## Lines and comparisons

- One main series should have a coherent accessible emphasis; competing series require distinct labels, not merely different hues.
- Do not require 100% stacked charts or arbitrary school comparison groups to depict a trend.
- Where a category transition or reset occurs, annotate it without pretending the old and new metric represent the same concept.
- A valid filtered set must reconcile with the actual records available to that viewer.
- A sparse dataset may be better as a sentence, card or table than a nearly empty plot.

## Loading, error and authorization

- A skeleton may approximate a chart's **shape**, but never display false real numbers.
- If refresh fails, show the **timestamp** of any valid earlier snapshot and explain that the latest data was not loaded.
- On logout, account switch or missing permission, protect prior user data. Admin access is not a blanket permission for individual learner records.
- Avoid repeated or duplicate events inflating apparent learning trends. See [Data reports](../design-patterns/data-reports.md) for common data integrity and retry rules.

## Accessibility and responsive layout

- Provide a plain-language description of the trend, meaningful labels, unit and time range.
- Make supported points/tooltips keyboard and touch accessible, not hover-only.
- Preserve readable Hanzi, tone-marked pinyin and localized text; move long x-axis labels or offer a table rather than rotate them into unreadable text.
- Check light and dark HSK AI colors, accessible contrast, text enlargement, phone safe areas and reduced motion.
- Do not use decorative red accents to imply an error or incorrect answer when the line only means a recorded quantity.

## Interactive HSK AI documentation example

The following demonstration contains **fictional example values only**. It illustrates a real UI interaction (switching view, sorting, state, or range), **not** a functioning HSK AI analytics endpoint or a new production screen.

> **Illustrative demo:** TrendReferenceDemo (fictional example; professional states remain documented in the guideline).

## Restored professional reference examples

> **Source-only illustrations:** Every figure below originated in a different product's design guidelines. Preserve their professional layout and interaction principles; do not treat sample students, school data, scores, source colors or buttons as verified HSK AI functionality.

### Overview

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Original trend-chart example with an illustrative time series, not HSK AI product history. Source asset: `./assets/trend-charts/header.png`.

Trends need **three or more comparable observed points** and explicit units, dates and filter scope. A sparse or missing dataset cannot be interpreted as steady growth.

### Anatomy

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Source example placing a time-series chart beneath summary metrics; values are source-only. Source asset: `./assets/trend-charts/container.png`.

**Time-series anatomy:** readable x-axis period, y-axis measurement with units, plotted observations and enough contrast to distinguish series without hue alone. Dates and missing periods must be accurately represented.

Place a high-level measure above the chart where useful; label the time window. Use a consistent interpolation policy: never draw a confident continuous increase across missing periods without marking the gap. If comparing groups, use the **same metric, sample definition, granularity and axis scale**. Describe which group each series represents for screen readers and provide an accessible table fallback when a production chart exists.

## Restored trend design rules

### Time axis and evidence

- Use a trend only for an **ordered series of genuinely recorded comparable periods**. One observation has no trend. When the analysis will permanently have only two points, a stat card expressing the verified difference is often clearer.
- Dates with unequal real intervals must use appropriately spaced time positions; named assessment windows can be equally spaced only when they are explicitly categorical periods. Label the time zone and granularity when a user could misread the boundary.
- Never convert a missing period into numerical zero or connect a line across an unknown value as if it were measured. Show a gap; distinguish future periods, incomplete reporting and not-yet-available data.
- For a line chart, **a nonzero vertical baseline can be appropriate** when clearly labeled; for bar charts, begin the value axis at zero. Do not exaggerate changes with an unlabeled truncated axis.

### Lines and labels

- A standard line is visually legible at about 2 CSS px before device-scale adjustments; prioritize contrast and touch visibility over rigid cross-platform pixel identity.
- Show point markers when there are only a few observations; with dense daily/weekly histories, reduce markers but retain keyboard/touch access to point values via a table or focusable summary.
- Label the most recent measured point and any point a conclusion explicitly references. Use exact units, date/period and sample population in the tooltip or alternative table.
- One highlighted series may use a stronger approved semantic color; other comparable series use neutral or distinct accessible roles with text/shape labels. Do not use an area fill when multiple overlapping lines would obscure one another.

### Comparing groups and trustworthy change

- Use equal time windows, calculation definitions, data freshness and account/permission scope. A change in tracking coverage, repeated events or learner mix must not be presented as individual progress.
- A reference line is legitimate only for an existing goal or compatible verified baseline. No invented school average, target or HSK mastery threshold.
- Prefer the statement “X verified activities over Y dates” to a directional claim if measurement coverage is incomplete. Surface a relevant loading/error state instead of freezing a stale chart as current.

## Implementation boundary

This document is HSK AI-only and deliberately contains no imported school test charts, source scoring examples or inherited comparator policies. Do not modify the app or manufacture trend data from the design guideline.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/trend-charts/header.png)

- [header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/trend-charts/header.png) — exact source blob `74ad90b6e1b3` (illustrated above)
