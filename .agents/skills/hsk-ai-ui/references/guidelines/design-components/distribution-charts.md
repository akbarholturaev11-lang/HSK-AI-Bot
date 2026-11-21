> **HSK AI professional design guideline — portable review copy.** Source: `__docs__/design-components/distribution-charts.mdx`, Git blob `cdfff090e0b6e8a69d034cd5be2d4b4b42c3a944`. 2 historic figure references and 0 MDX demo blocks; source images / vendor runtime code were not copied. Source prose remains an internal derivative draft pending rights and detailed visual parity review; this does not assert a live app feature.

# Distribution charts

*Component role: Verified range distribution*

Distribution charts answer **“How are the actual observations spread across defined ranges?”** They can help an authorized HSK AI report show counts of supported learning records or mastery states, where those categories are genuinely tracked. They do not imply a school assessment feature or an extra HSK AI analytics endpoint.

## When to use

| Use when | HSK AI requirement |
| --- | --- |
| Readers need to understand the spread across ranges | Use real, mutually exclusive categories and a verified population/denominator. |
| Readers need to see the low or high end | Include a **zero/none** bucket when zero is possible; do not hide the records most in need of review. |
| Two time windows need comparison | Use the same metric, range boundaries, scope and permission model in both windows. |
| Data has meaningful real learning bands | Match only actual recorded HSK definitions and available score categories, never a different product's grading bands. |

## When NOT to use

- For one fact or a tiny genuine population, choose a [summary card](summary-cards.md) or table.
- For chronological movement across three or more periods, use [trend charts](trend-charts.md).
- For exact individual learner/lesson values, use an authorized [table](data-tables.md).
- Do not build peer/school comparisons or benchmark levels that HSK AI does not record.

## Anatomy

| Part | Rule |
| --- | --- |
| Title | A factual, helpful takeaway for the actual measure and scope, never an invented statistic. |
| Category axis | Ordered, disjoint ranges with descriptive labels and a consistent unit. |
| Value axis | Counts or percentages, starting at **zero**; state the denominator for percentages. |
| Bars | Choose the actual semantic theme colors; avoid misleading per-bar colors. |
| Labels | Provide values on/near bars and accessible text equivalents. |
| Controls | Real data-range/filter controls that affect only their labeled scope. |
| Timestamp | If freshness is relevant, use the verified update time rather than pretending the records are current. |

Use the existing [chart container](chart-container.md) pattern where a supported report provides it.

## Range design

1. Usually choose **4–8** meaningful ranges, but do not manufacture artificial HSK score bands to reach that count.
2. Keep ranges equal width where the unit permits; if an existing learning classification defines uneven ranges, use its **actual official boundaries**.
3. Show zero and empty ranges explicitly; do not remove empty bars to make a distribution look smoother.
4. If the measure has no maximum, a clearly labeled final open range (such as `11+` for a real count) prevents silent exclusion.
5. Preserve the **same** ranges across periods/groups. Never recompute a new range set for each series when making comparisons.
6. Never sort ordered ranges by bar height; that changes a distribution into a ranking.
7. Use clear labels rather than rotating small or lengthy Chinese/translated labels. Horizontal bars are preferable when phone width or accessibility scaling makes labels unworkable.
8. If a chart supports drilling into a filtered list, reconcile its bar count with the actual authorized records. Do not invent that interaction just because the graph has bars.

## Two comparison variants

### Grouped by a real level

Use level bands only if the metric already defines valid, distinct HSK or learning mastery groups. A level count must equal the sum of its bars, and an observation must not be counted in multiple exclusive bands. The level name and count must be accessible without color.

### Two periods side by side

For the same population and measure, show two bars per category with a common zero baseline, clearly named periods and consistent ranges. If inclusion requires observations in **both** periods, state the eligible and excluded counts. Do not reclassify absent records as zero. For more than two simultaneous periods prefer a trend chart, where appropriate.

### Comparing groups

Only compare groups that an authorized user is allowed to access, and that share equivalent event definitions. A learner-facing report is owner-scoped by default; aggregated admin reports require their own access controls and privacy safeguards.

## Missing data and failure

A missing event is not a zero. Mark incomplete collection, processing, unsupported platform coverage and genuinely empty categories differently. Do not show stale totals as current or mix HSK course versions with incompatible definitions.

An isolated chart error should not prevent independently loaded report components from being read. See [HSK AI data reports](../design-patterns/data-reports.md) for loading, empty, retry and owner-verified access rules.

## Accessibility and mobile

- Provide a text summary of the actual finding, explicit units, an accessible name for each bar and appropriate color contrast.
- Make supported tooltip/detail interactions available on **touch and keyboard** without relying on hover alone.
- Respect narrow screens, localized Cyrillic/Chinese labels, tone-marked pinyin and enlarged text. If vertical categories become illegible, switch to horizontal or a table.
- Use real HSK AI colors, not a borrowed assessment palette. An incorrect-answer red or brand accent is not by itself an acceptable chart category legend.

## Interactive HSK AI documentation example

The following demonstration contains **fictional example values only**. It illustrates a real UI interaction (switching view, sorting, state, or range), **not** a functioning HSK AI analytics endpoint or a new production screen.

> **Illustrative demo:** DistributionReferenceDemo (fictional example; professional data/visual states are documented in this guideline).

## Restored professional reference examples

> **Source-only illustrations:** Every figure below originated in a different product's design guidelines. Preserve their professional layout and interaction principles; do not treat sample students, school data, scores, source colors or buttons as verified HSK AI functionality.

### Overview

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Original distribution chart overview with illustrative source groups. Source asset: `./assets/distribution-charts/header.png`.

A distribution is a **count across mutually exclusive bins**, not a progress bar or a trend. Define the denominator and bin boundaries explicitly.

### Anatomy

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Original histogram layout reference; source scores and school ranges are not HSK AI measurement rules. Source asset: `./assets/distribution-charts/container.png`.

**Histogram anatomy:** consistent range labels, zero baseline and appropriately grouped bars. The total count of observations must reconcile with the displayed bins and exclusions.

Do not assign a learner's HSK level to a score bin unless such mapping is supported in real data. For comparing two periods, align bins, units, sample scope and the denominator; otherwise the difference is misleading. Distinguish *not measured* from the numeric zero bin. Use readable labels and a data table alternative for accessible chart implementations.

## Restored distribution design rules

### Ranges and sampling

- Prefer **four to eight clearly labeled bins** when a distribution genuinely needs ranges; use additional bins only when an actual scoring or learning taxonomy demands them. Include a dedicated “none” or zero bucket whenever zero is valid.
- Use non-overlapping, mutually exclusive boundaries, readable units and a stable sorting direction. Equal-width numeric bins make heights comparable; **real categorical levels must follow the actual level definitions** even when widths differ.
- State whether the bars count **unique learners, attempts, activities or vocabulary entries**. Never sum attempts as learners. Check that included bins plus explicitly disclosed exclusions reconcile to the authorized denominator.
- Do not publish a granular small-cohort chart when it might expose another learner's results. A short text summary or authorized table can be more appropriate when the sample is too small.

### Chart anatomy and comparisons

- Value bars start at **zero** and share a labeled count/percentage axis. Put exact values in data labels or an accessible alternative; do not rely on color or hover.
- Use a description that identifies the metric and included population, not merely “Results.” Use a count and denominator for percentage labels and show the sample size when comparing rates.
- Two time periods must use **identical boundaries, units, learner/event definitions and available permission scope**. Comparing distinct learner cohorts is not evidence that individual learners improved.
- For group comparison, align the axes, category order and units; avoid a misleading stacked arrangement if readers need exact side-by-side comparisons.
- A tooltip is optional supplementary detail and, if added, must work with touch and keyboard. A bar can navigate to a verified filtered list only if that route and authorization already exist.

### Misuse prevention

- Use a trend chart for change across ordered time, a progress chart for a real goal, and a table for exact individual records. Do not draw a histogram when one count already answers the question.
- Missing, excluded, processing and confirmed zero observations are distinct. Do not insert zeros or fabricate HSK pass bands to force a complete chart.

## Scope

This guideline contains no source-school assessment charts, currency, grade taxonomy or generic mock score data presented as production truth. It does not change the actual HSK AI analytics pipeline or introduce new chart functionality.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/distribution-charts/header.png)

- [header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/distribution-charts/header.png) — exact source blob `8d9ed89b089d` (illustrated above)
