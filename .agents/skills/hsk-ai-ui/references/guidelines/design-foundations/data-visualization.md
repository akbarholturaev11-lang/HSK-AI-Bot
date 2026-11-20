> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/data-visualization.mdx`, Git blob `7ea71c7140c99699d80a9082d030200f82886bbb`; 0 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# HSK AI data visualization

Visualize **actual verified HSK AI learner activity** and **separately authorized admin analytics**. A useful chart communicates a question's answer with as little decoding as possible. This foundation does not create metrics, grading scales, analytic endpoints, comparison groups or a new chart renderer.

See [Data reports](../design-patterns/data-reports.md) for report layout, filtering, failure and authorization; component pages cover [summary](../design-components/summary-cards.md), [progress](../design-components/progress-charts.md), [trends](../design-components/trend-charts.md), [distribution](../design-components/distribution-charts.md) and [tables](../design-components/data-tables.md).

## Principles

1. **Truthful and verifiable:** every count, denominator, timestamp, scope and source event must be real and correctly recorded.
2. **Helpful:** show the specific lesson, learning goal or study-action insight relevant to this learner and the selected period.
3. **One question per visualization:** if one sentence or a number is clearer, use that instead of a graph.
4. **Accessible:** use readable values, labels, patterns and explanations; no insight depends on hue or hover alone.
5. **Owner and permission aware:** a learner sees their own verified progress; administrative analytics require explicit authorization.
6. **Mobile-first:** respect PWA/Android screen width, keyboard, text scaling, Hanzi/pinyin and the actual UI's interactive controls.

## Choosing a chart

| Question | Preferred form |
| --- | --- |
| What is the single verified value? | Summary card |
| How far along is an actual measured goal? | Progress |
| How do verified observations spread across categories? | Distribution |
| How has a comparable metric changed over several periods? | Trend |
| Which exact event/lesson/word value is recorded? | Authorized data table |

Use ordered bars with a true zero, appropriate line scales for real time series, and meaningful numerical axes. Avoid 3D, overly complex pies, unlabelled gauges and overlapped filled areas that distort comparison.

## Anatomy

| Part | Purpose |
| --- | --- |
| Heading | Names the actual learning measure or report scope |
| Chart title | Gives a factual takeaway supported by values |
| Description | Explains relevant period, event definition, HSK version and denominator |
| Axes | Real units and correctly spaced scales |
| Data marks | Bars, lines or points encoding true values |
| Direct labels | Counts/values where needed to interpret marks |
| Legend | Text/pattern key only if series cannot be labelled directly |
| Tooltip | Optional extra details, accessible on touch and keyboard |
| Footer | Last successfully refreshed or audited time where data freshness matters |

Use [Chart container](../design-components/chart-container.md) to frame a real graph; it is a layout pattern, not a mandated UI package.

## Color

Chart color describes the **meaning of the measure or comparison**, not a source design system's product palette. Use the **professional semantic hierarchy and visual encoding** as the target, mapping it onto verified HSK AI light/dark token roles. If current tokens are insufficient for correct distinction or contrast, specify a proposed token/role rather than abandoning professional chart quality; verify actual rendered contrast later. See [HSK AI semantic colors](colors-semantic.md).

### Color roles

| Role | Meaning | Guard |
| --- | --- | --- |
| Progress and amounts | Real recorded completion or a verified goal | Pair with count/denominator, not an invented grade |
| Categorical | Distinct observed options | Use clear labels, avoid too many competing series |
| Neutral | Unselected reference or a genuinely grouped “Other” category | Do not hide missing records |
| Emphasis | Highlight a comparison's relevant value | Do not turn emphasis into praise or error |
| Annotation | Verified date, target or milestone | Only when an actual comparable reference exists |
| Scores | An actual tracked exercise or test result | The score and course's real threshold come from product logic |
| Motivation | Real recorded streak/XP/milestone, if tracked | Do not invent a separate points economy or reward |
| Errors | Failed or incomplete chart loading | A clear localized status and recovery, not just a red bar |
| Assessment | An available verified quiz outcome | Not equivalent to completion percentage or time spent |
| Mastery | Existing vocabulary/learning mastery definition | Never import an unrelated grading taxonomy |

**Do not invent token names** such as `--hsk-critical` when absent from the actual HSK AI token file. Inspect existing component error styling and propose additional roles only in a separate validated implementation. The product brand-action color may not double as an unambiguous error state. Wrong-answer feedback uses both text/icon and the approved lesson character reaction when supported.

### Series and contrast

- Limit simultaneous series to a clearly readable set and label them directly where possible.
- Use at least appropriate non-text contrast (generally 3:1 when meaningful) and normal-text contrast (generally 4.5:1), tested in both actual themes.
- Do not color an exercise's **low but valid recorded score** as a UI error without a real semantic reason.
- Do not rely on monochromatic red bars merely because red is the light-theme product accent.

## Typography and numbers

Use HSK AI's actual [Typography](typography.md) system. Hanzi characters, marked pinyin and localized translations may be important data labels; don't clip or abbreviate away their distinctions.

### Number formatting

- Display the metric's actual unit: lesson count, attempt, correct answers, minutes, percentage, XP where verified.
- For percentages, give a numerator and denominator when useful, e.g. **12 of 15 lessons (80%)**, but **only** when those records are real.
- Round only to precision meaningful for a decision; don't create precision the measurement cannot justify.
- Compare rates for differently sized groups and clarify which records were included.
- Use localized separators and dates where appropriate; do not mandate English-only or US date formatting.
- For large values, compact formatting is fine when it doesn't hide an important difference or a tiny denominator.

### Missing and zero values

- **Zero** means measured and confirmed as zero: display `0`.
- **Missing** means no usable observation: show an appropriate unavailable marker or explicit explanation.
- **Processing** means the collection is not yet finalized; no invented “completed” count.
- **Stale** requires the actual last-successful-update time where relevant.
- A missing/unsupported Android or PWA event is **not** zero. Duplicate events are **not** additional learners.

## Interaction

- Tooltips and point details, if present, work on touch and keyboard, not hover alone.
- A chart/table switch, export or legend toggle must be **offered to end users only if implemented and authorized**. Preserve the professional layout and interaction specification as an **unimplemented reference** otherwise; do not delete it merely because today's HSK AI app lacks the control.
- All dependent figures, filter scopes, time windows and summaries should update consistently when real controls are used.
- Do not render protected data after logout/account change.

## Writing for data

Use accurate plain-language titles that say what the data shows, with actual units, date range and context. Avoid unverified predictions, fabricated scores, arbitrary peer comparisons or school-specific language. The display may be condensed, but not at the expense of accuracy or readable localization.

## Accessibility

Every chart needs a text summary and, for complex values, an accessible detail/table alternative. Non-text data marks should have meaningful labels; color cannot carry an entire chart's meaning. Screen readers, keyboards, large text, mobile orientation and reduced-motion users must be able to understand the same real fact.

## Restored professional chart and data-writing checks

### When a chart misleads

- Choose a **number** when one verified value answers the question, a **chart** when position/length over groups or time conveys a pattern, and a **table** for exact records and actions.
- Prefer a simple bar or line to ambiguous angle/area encodings. Avoid multi-slice pies, dials and overlapping area charts when a labeled bar, progress measure or table makes comparison more accurate.
- **Bars start at zero.** Line axes may have a labeled nonzero minimum, but never make a small change look dramatic by hiding the scale. Mark measurement gaps instead of connecting them as if observations existed.
- Use one insight per chart. If the finding depends on comparing many distinct colors or too many dimensions, split the view or offer a table. Treat four distinguishable series as a *clarity heuristic*, not a statistical or app cap.

### Quantities, denominator and typography

- A chart's name, axes, labels, unit, scope, time window, aggregation method and significant exclusions together define the claim. Each displayed percentage needs a real denominator; an empty denominator cannot be called zero percent by assumption.
- Use readable numerals in the current locale; avoid rounding that makes visible parts fail to sum to the total without explanation. Keep the full precision available when the decision relies on it.
- A **confirmed zero** is a measured observation. Not recorded, not applicable, insufficient data, still processing, stale, permission-denied and network failure are **different states** and must be communicated differently.
- Values embedded in chart marks and legends require proper text size, number formatting and contrast. Keep labels visible under zoomed text and Chinese/Russian/Tajik/Uzbek localization where applicable.

### Accessibility and data provenance

- Never distinguish correct/incorrect or good/bad solely through red/green. Use direct numeric labels, shape/pattern, icon and explicit status wording.
- Required visible chart strokes and graphical controls need at least **3:1** contrast against the actual background; ordinary text targets **4.5:1**, subject to the applicable WCAG exceptions. Test both HSK AI themes; do not claim that untested existing pairings pass.
- Provide a text takeaway and a usable keyboard/touch accessible data alternative. Hover-only point details are insufficient for phones and assistive technology.
- A reported trend or comparison must specify whether data came from PWA, Android or deduplicated cross-platform observations. Never mix event definitions, log retries, consent states or reporting freshness silently.

## Verification before implementation

Validate against the current HSK AI app data model and backend event definitions, real analytics coverage, PWA/Android platform differences, server ownership and view permissions. Never claim that an untested chart has shipped or that the application has a metric not recorded in its source.
