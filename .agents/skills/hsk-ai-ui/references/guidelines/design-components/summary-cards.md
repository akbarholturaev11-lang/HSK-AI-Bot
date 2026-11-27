> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/summary-cards.mdx`, Git blob `59720700a5d84a512397e092e003e9d89d8842f1`; 3 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# Summary cards

Summary cards communicate **one verified, scoped HSK AI fact** without asking readers to decode a chart. They may be used for a learner's real study progress or an authorized administrator's validated metric, where the product actually provides such data.

## Variants

### Stat card

One meaningful number with a specific label and, where relevant, a unit, denominator or time frame. Never fill a card grid with hypothetical XP, streaks, payments, starts or completions.

### Comparison card

One current value and one genuinely comparable previous value, with time frames and direction made explicit. Missing or partially recorded prior data is **not zero**.

### Drill-down card

Include an action only if a real screen provides a working, authorized destination and the link's label describes what opens. Do not introduce classroom or school report destinations merely to decorate a stat.

## Anatomy and hierarchy

| Element | Professional rule |
| --- | --- |
| Metric name | State the real learning result or product metric unambiguously. |
| Value | Show the exact verified number and appropriate unit or percentage. |
| Period and scope | Show which learner/HSK level/platform/date range the number covers. |
| Status | Indicate processing, incomplete or stale values explicitly. |
| Comparison | Only for compatible periods and definitions; pair an arrow with readable text. |
| Action | Optional, only for a real next step or permitted detail page. |

## Usage rules

1. Use a summary card when a single number is more informative than a graph.
2. Do not show success-colored metrics before the authoritative learning or payment state confirms completion.
3. Do not mix learner-facing private progress and unrelated admin analytics in one surface.
4. A card with no data should show an honest empty/unavailable state, not `0` unless zero has been verified.
5. Use consistent formatting and the chosen learner language, including proper Hanzi/pinyin labels where actually present.
6. Keep the reading order readable on iPhone PWA and Android; wrap long translations rather than shrinking essential words to decorative microtype.
7. If several related cards are displayed, order them by the user's information need; do not force a desktop grid onto a phone.
8. Critical payment terms, privacy limits and server errors are not optional two-line disclosures.
9. Trends require verified comparison values, real time windows and explicit direction; do not invent a school or peer average.

## Loading, errors and access

Show stable known card labels while the metric loads. A refresh failure may retain a valid previous number with an explicit timestamp, but never claim it is current. Protect previous account data on logout/switch. Offer retry only when an actual retry action exists.

Refer to [Data reports](../design-patterns/data-reports.md) and [Data visualization](../design-foundations/data-visualization.md) for shared reporting and accessibility rules.

## Restored professional reference examples

> **Source-only illustrations:** Every figure below originated in a different product's design guidelines. Preserve their professional layout and interaction principles; do not treat sample students, school data, scores, source colors or buttons as verified HSK AI functionality.

### Overview

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Historical summary card layout example containing source metrics, not real HSK AI analytics. Source asset: `./assets/summary-cards/header.png`.

A summary strip should lead with a verified high-value number and its period; secondary comparison does not overpower the figure.

### Anatomy

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Original example of plain stat cards and directional badges; the sample scores are not HSK AI grading rules. Source asset: `./assets/summary-cards/stat-cards.png`.

**Stat card:** include metric label, value, unit and time period. A color-coded upward/downward indicator must only describe a real comparable change, with a readable explanation.

### Controls and comparison

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Source example of summary cards with explicit links to detailed views. Source asset: `./assets/summary-cards/stat-cards-clickable.png`.

**Actionable card:** only show a View/Details affordance if a supported destination exists and the user is authorized. A clickable card requires focus, keyboard semantics and a visible destination label.

Do not merge *enrolled*, *active*, *completed*, *passed* and *Pro* into one undefined status. A summary value must carry the same account, platform, date range and deduplication rules as its drill-down list. On phones allow the value and localized labels to wrap; avoid tiny fonts or misleading down arrows. Loading, partial coverage, missing permission and failure are different states.

## Restored summary-card usage and anatomy

### Decide when a card is appropriate

- Use a card for **one important, directly understandable verified metric**. Position small groups after the page/section heading and before deeper charts or tables; on phones, a single full-width readable card is preferable to a forced multi-column grid.
- Use a trend chart for change over time, a distribution for group spread, a goal bar for completion and a table for record-level actions. A stat card cannot show those dimensions honestly.
- A detail link appears only if the detail route really exists and the user may access it; its accessible label must state the destination rather than merely “View.”

### Stat anatomy

- Pair a **one-to-three-word label** with an exact value and unit. Add scope, period, denominator, freshness or explanation when leaving them out changes interpretation.
- A trend badge may communicate a verified change from a compatible baseline, but an increase is not automatically success and a decrease is not automatically failure. For error-rate metrics the meaning may be reversed.
- Do not invent peer ranking, learner percentile, streak, XP, HSK level or “class average.” Show a missing value distinctly from zero, loading, access denied, partial and stale states.
- Keep related cards consistent in emphasis/alignment while allowing localized labels and larger text to wrap. Do not clip Hanzi/pinyin, status or denominators for visual symmetry.
- A clickable card must have a single coherent focus/activation target with keyboard and screen-reader support; a non-clickable metric must not look like a button.

### State accuracy

- When the metric cannot load, label the **specific metric** unavailable without hiding valid adjacent cards. A retry must not manufacture data, restart payment or post a lesson event.
- Card aggregates, corresponding charts and underlying table lists must use one verifiable definition and matching permissions.

## Implementation boundary

This document defines HSK AI summary-card design only. It contains no school/district report examples or fictitious production metrics. It does not alter analytics, scoring, progress or payment code.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/summary-cards/header.png)

- [header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/summary-cards/header.png) — exact source blob `564750752231` (illustrated above)
