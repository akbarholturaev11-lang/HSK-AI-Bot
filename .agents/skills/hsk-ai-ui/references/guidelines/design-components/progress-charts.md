> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/progress-charts.mdx`, Git blob `b68a79840726291984c6227ce997fa4938176551`; 2 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# Progress charts

Progress charts answer **“How much of this verified, measurable goal is complete?”** A current amount and a real goal are both required. A learner's verified HSK AI lesson progress, a configured activity target or an authorized admin metric may qualify, **only if the relevant current app state actually records both quantities**.

## When to use

- An actual numerator and denominator exist and refer to the **same unit, learner/account scope and time window**.
- An authorized user benefits from seeing how much remains rather than an isolated score.
- A genuine configurable schedule defines a meaningful “expected by today” threshold; this marker must be computed from that schedule, never invented.

Do **not** use this component to assign an exercise grade, invent an HSK pass threshold, draw a class-assignment bar or create a Gem/reward system. A correct answer, progress toward a goal, a score, a streak and Pro entitlement are different states.

## Anatomy

| Part | Requirement |
| --- | --- |
| Title | Name the real HSK AI goal or task. |
| Current amount | Server-verified value with meaningful units. |
| Target | Actual configured amount, never a source-chart constant. |
| Progress bar | Represents `current / target` on a common, nonmisleading scale. |
| Remaining amount | If useful, calculate from the verified goal; do not turn missing data into zero. |
| Time/expected marker | Show **only** if a real schedule and its method have been defined; otherwise omit. |
| Text alternative | Clearly announce current, target, units and any real shortfall. |

Bar visuals follow the **professional semantic hierarchy, geometry and state model**, mapped onto real HSK AI light/dark semantic colors or a clearly proposed role. Neither the old app's contrast flaws nor foreign assessment/reward palettes are the target.

## Visual and mathematical rules

1. A bar starts at **zero**. An amount above the target may be represented as `100% complete` with a separate, plainly labeled excess, but never silently shorten the real count or fabricate progress over the goal.
2. Never mix different units within one bar set. If two measures differ, use separate views.
3. Use a verified numerator and denominator; filter and permission scopes must match. Never classify an unrecorded Android or PWA event as incomplete work.
4. Avoid coloring a bar as wrong/error merely because the target was not reached. A missed genuinely time-bound obligation needs separate, explicit status.
5. For comparison across multiple authorized records, the goals must share a compatible definition and time window. A learner view cannot reveal other learners' private progress.
6. When values are not yet known, show a loading state or an honest unavailable state, **not** a sample count.
7. Labels and bars must remain readable in compact phone layouts, both themes and text scaling. Keep actual values outside a bar if interior text would be too small.
8. Do not force a “today” target from calendar weekdays or school-day formulas. Only current product schedules define that marker.

## Containers and variants

**Compact:** one goal, current value, target and simple progress. Use an ordinary card when nothing else needs attention.

**Detailed report:** a single supported objective with a title, verified date range and optional action. Link to detail only when an actual authorized destination exists.

**Multiple comparable goals:** use aligned bars if readers need to compare compatible real records; use a table when labels or unit differences make a chart misleading. Color is not the only progress cue.

## Empty, error and outdated state

- If the goal has not been set, explain that state instead of drawing `0 / 0` or a 0% bar.
- If the goal exists but no observations were made, distinguish **actual zero** from **missing records**.
- When data fails to refresh, preserve a valid prior snapshot only with a clear timestamp and visible retry.
- On account changes, validate record ownership and clear protected stale values.

Use [HSK AI data reports](../design-patterns/data-reports.md) for common report behavior, and [Data visualization](../design-foundations/data-visualization.md) for color/number/accessibility guidance.

## Accessibility

Each chart announces the actual value and goal as text, with a clear accessible name and unit. Do not depend on color, animation, a vague percentage or a character reaction alone. Check focus, contrast, dynamic text size and mobile safe areas. Reduced-motion mode must still convey the completed amount and any genuinely pending task.

## Interactive HSK AI documentation example

The following demonstration contains **fictional example values only**. It illustrates a real UI interaction (switching view, sorting, state, or range), **not** a functioning HSK AI analytics endpoint or a new production screen.

> **Illustrative demo:** ProgressReferenceDemo (fictional example; professional states remain documented in the guideline).

## Restored professional reference examples

> **Source-only illustrations:** Every figure below originated in a different product's design guidelines. Preserve their professional layout and interaction principles; do not treat sample students, school data, scores, source colors or buttons as verified HSK AI functionality.

### Overview

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Source progress chart overview; it is not HSK AI's Gems or school reward feature. Source asset: `./assets/progress-charts/header.png`.

A progress bar requires a real, validated numerator and target in the **same units**; otherwise use a different view.

### Anatomy

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Original large progress-chart container showing current versus target observations. Source asset: `./assets/progress-charts/container.png`.

**Progress anatomy:** clear title, measured current amount, real target, optional marker only where an actual schedule exists and meaningful completion semantics.

Never use an expected-by-today marker or 100% unless the backend records the target and its schedule. Preserve a readable text equivalent for bar fill; distinguish a goal that is exceeded from an error in accounting. Compact versions omit secondary controls without hiding the actual current/target values. **Gems challenge illustration remains excluded** because HSK AI has no corresponding verified reward metric.

## Restored progress design rules

### Choose progress rather than a score

- A progress bar measures **completion of a real task toward a genuine target**. A learning grade, answer correctness, mastery status, unverified XP total or subscription entitlement is not automatically completion progress.
- Without a genuine target, use a stat card for the current amount. Use a trend for change over time and a distribution for counts by band. Avoid circular gauges when a linear bar communicates the same result more precisely.
- Show **current value and target together**, in the same units and account/date scope. For example, use “8 of 12 verified lessons” only if both quantities come from the authorized course state.

### Title, bar and expected marker

- Use a concrete title, an exact numeric label and a denominator. When a real schedule exists, say how far ahead or behind the learner actually is; do not add “on track” from a guessed deadline.
- A bar starts at zero, advances monotonically for actual completed units and has an accessible numeric text equivalent. Distinguish “target achieved” from “value unexpectedly greater than denominator”; do not hide data-integrity issues with CSS clipping.
- **Expected by today** is optional and requires a stored real target, time zone, schedule and transparent formula. Label the expected amount; without reliable scheduling data, omit the marker entirely.
- A large container can show marker, explanation and genuine controls. A compact card uses one bar and the essential values only; it must not silently discard the denominator.
- Comparing multiple groups requires the **same measurement and same goal definition** for all bars. If one group uses a different target, separate the charts or clearly normalize with an explained method.

### States and accessible reporting

- Loading, no target, no observations, missing permission, outdated records and request failure must not look like 0% completion.
- Expose the number/target to a screen reader in the user's locale; distinguish completion from grades and incorrect-answer feedback. Keep the icon/character lesson reactions intact.

## Implementation boundary

This is an HSK AI guideline, not a prebuilt progress chart or an instruction to edit learning/scoring endpoints. It deliberately removes source-school, grade-target, Gem and assignment chart demos after retaining their valid general progress principles.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/progress-charts/header.png)

- [header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/progress-charts/header.png) — exact source blob `133c27c0edc2` (illustrated above)
