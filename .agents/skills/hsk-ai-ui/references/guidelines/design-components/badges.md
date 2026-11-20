> **HSK AI professional design guideline — portable review copy.** Current implementation is not implied. Source `__docs__/design-components/badges.mdx` (Git blob `048a1b078fb60af241881ffe44be440505c14a06`); 19 historic figure references, 0 MDX demo blocks. Approved neutral example PNGs are linked below where available; excluded foreign screens and vendor runtime code were not transferred. The original prose remains an internal source-derived draft. Full professional prose is retained as an internal source-derived draft.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Badges. Source asset: `./assets/badges/badges.png`.

# Badges

> **HSK AI adaptation:** This guideline applies only to **real verified HSK AI states**. Display short readable status text; do not apply screenshot-specific scores, account roles or metrics as product requirements.

*Component role: Status/Meta-data indicators*

A small, contextual, non-interactive container used to display a single, non-critical piece of meta-data or communicate a current status associated with a larger object.

## Recommended: When to use

The choice to use a badge is determined by the need for a brief, immediate visual communication of status or category.

| Use when | Example use |
| --- | --- |
| Describing the state of an adjacent object (not standalone) | Displaying a **verified** HSK AI lesson completion state next to the corresponding lesson title, when that state is known. |
| Communicating a status with a single word or short label | [Draft], [Published], [Overdue], or [On Hold]. |
| The status is read-only — not a button or link | Showing an actual, verified item-level status such as a recorded lesson completion; do not invent a teacher attendance workflow. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| Signaling a system-wide critical alert | Transient message (toast or banner) | Do not use for global, session-wide errors or urgent system feedback (a service outage, a failed save). Badges label the state of a specific item, not the system as a whole — see Critical error status below for that distinction. |
| Labeling a permanent identity or category | Tertiary text, tag, or chip | Do not use a badge for fixed HSK level names, course titles, static user identifiers or other permanent categories. Badges represent state; ordinary labels represent identity. |
| Prompting a call-to-action | Button or link | Do not use a Badge to drive a user to click or perform an action. They communicate what is, not what to do. |
| Displaying complex meta-data | Tooltip or inline text | Do not use for conveying long, multi-line data or complex contextual help. If the information cannot fit into one word, use a tooltip or standard text. |
| Categorization is already established visually | Tertiary text or omit entirely | If an accompanying illustration or icon already establishes the category/identity, do not use a badge. Use subtle tertiary text to provide the label without competing for visual attention. (ex. Insight card) |

## Variants

### Critical error status

This category is reserved exclusively for signals that communicate risk, failure, or urgency about a specific item — not a system-wide alert (see When NOT to use). The color must be used to trigger an immediate “Stop and Address” behavior from the user.
Do signal a critical error when inaction has a negative consequence (missing a deadline, failing score, data failure).

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Variants 1. Source asset: `./assets/badges/variants-1.png`.

### Warning status

This category communicates a state of potential trouble, pending risk, or non-blocking issues that require user attention and review, but do not necessarily prevent the current task from proceeding. The color should be used to encourage a "Review and Proceed with Caution" behavior.
Show a genuine pending state, verified risk, or recorded drop in a learning metric when the item warrants review. Do not infer classroom activity or unverified scores.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Variants 2. Source asset: `./assets/badges/variants-2.png`.

### Success status

This category is used exclusively to confirm that a positive, goal-achieving, or completed action has successfully occurred. It provides immediate, reassuring confirmation that a process or step is finalized.
Do signal completion and use the green success badge for items that are verified, finished, approved, or functioning normally (complete, good score, increase in metric).

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Variants 3. Source asset: `./assets/badges/variants-3.png`.

### Neutral status

This category is for communicating a general status, category, or phase that is neither positive (Success) nor negative (Warning/Critical). It simply describes the current state.
Do use a neutral badge for items that are general, such as those that are currently being worked on (in-progress, draft), those that are awaiting a decision (pending review), or those that are in a stable, non-alert state while awaiting a future action by the system or user (scheduled or on hold).

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Variants 4. Source asset: `./assets/badges/variants-4.png`.

### Time status

This category communicates necessary, non-urgent information that is tied to a deadline, feature discovery, or temporary discovery.
Do use this badge to communicate that something is due and when it is due, such as Due tomorrow, Due Friday, Due 11/6.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** Variants 5. Source asset: `./assets/badges/variants-5.png`.

### Informative/feature status

This category is designed to draw attention to new or special functionality. It signals that a component has a temporary or unique quality the user should know about.
Do use this badge to flag an active feature mode or temporary discovery. Badges that communicate discovery, like New, must expire after two weeks as the default. If a different expiration timeframe is needed, that should be determined on a case by case need.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** Variants 6. Source asset: `./assets/badges/variants-6.png`.

### Verified metric status

Only an **actually tracked and verified** HSK AI metric may receive a compact badge. Include a correct unit and scope. Do not invent a source-product currency or rewards system.

## What goes inside the badge

Badges highlight only the noteworthy fact — not everything around it. What goes inside the badge depends on what it's representing.

### Status and category badges

When the badge represents a discrete status with no separate number attached — Draft, Published, Complete, Integrity violation — the full short label belongs inside the badge. There's nothing to separate out; the label itself is the entire fact.

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** Status and category badges with the full label inside: Integrity violation, Unactivated, Activated. Source asset: `./assets/badges/states-1.png`.

### Value and trend badges

When the badge represents a number, percentage, or directional change, keep only the value and its icon inside the badge (↓ -6.3%, ↑ 12%) — or the icon alone when there's no specific number to show. Any text describing what the value refers to (a time period, a category) is a caption explaining the fact, not the fact itself, and stays outside the badge as plain text.

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** Value and trend badges: keep only the value and icon inside (↓ -6.3%, ↑ 12%) with the describing label as plain text outside, rather than bundling the label into the badge. Source asset: `./assets/badges/states-5.png`.

## Iconography

### When to include icons

Do include an icon only if it instantly conveys the same meaning as the text (a checkmark for "Complete"). Don’t use icons if it requires a cognitive jump or interpretation. If the badge works just as well without the icon, then omit the icon to reduce visual noise.

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** States 2. Source asset: `./assets/badges/states-2.png`.

### Truly standalone icons

A bare icon with no text anywhere nearby at all should be reserved for universally understood null indicators, such as a dash (—) for "No data" or "Not assigned." A bare icon with plain text beside it (like an arrow next to "above actual recorded trend") is a value or trend badge — see Value and trend badges above.

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** Do and don't examples of standalone icon badges: a bare dash for null data is acceptable, while icon-only trend and status badges without text are not. Source asset: `./assets/badges/iconography-1.png`.

### Icons that can change

Success and warning badges have exactly one icon substitution allowed: a plain up or down arrow, used only when directly indicative of a metric trend. No other icon swaps are permitted — not a stylized trend arrow, not a decorative icon like confetti, nothing else. For all other cases, use the default system icon.

> **Historical figure 12 — source figure reference (only approved samples, if any, are linked below):** Conditional success and warning icon use: default system icons and up or down arrows for metric changes are acceptable; arbitrary icons such as a diagonal arrow or confetti are not. Source asset: `./assets/badges/states-3.png`.

### Icons that cannot change

Critical and time status badges use stable, understandable symbols; a source product’s currency icon is not an HSK AI requirement.

> **Historical figure 13 — source figure reference (only approved samples, if any, are linked below):** States 4. Source asset: `./assets/badges/states-4.png`.

## Score to status mapping

### Scoring semantics and thresholds

Use the **actual HSK AI learning and assessment scoring specification** and server-verified status. This badge system imposes **no universal numeric pass/fail thresholds**. A correct answer, a passed course, a completed lesson and a Pro entitlement are different states.

### Neutral status

Use the neutral badge exclusively for communicating the current status of a process or progress state, including labels like "In progress," specific percentages like "50% complete," and initial states like "Not started".

> **Historical figure 14 — source figure reference (only approved samples, if any, are linked below):** Score to status mapping 2. Source asset: `./assets/badges/score-to-status-mapping-2.png`.

### Null data handling

Do not use text for non-applicable or unassigned data; instead, use a simple dash (—) or null indicator to maintain alignment in tables.

> **Historical figure 15 — source figure reference (only approved samples, if any, are linked below):** Score to status mapping 3. Source asset: `./assets/badges/score-to-status-mapping-3.png`.

## Copy

### Brevity

Keep text to a maximum of 3 words so the user can process the information instantly, without breaking their reading flow.

> **Historical figure 16 — source figure reference (only approved samples, if any, are linked below):** Copy 1. Source asset: `./assets/badges/copy-1.png`.

### State status directly

Do describe the status in the most neutral and factual way possible.

> **Historical figure 17 — source figure reference (only approved samples, if any, are linked below):** Copy 2. Source asset: `./assets/badges/copy-2.png`.

### Sentence case

To be consistent with UX copy guidelines, use sentence case.

> **Historical figure 18 — source figure reference (only approved samples, if any, are linked below):** Sentence case badge copy: 'Flagged by moderation' is correct, 'Flagged By Moderation' is not. Source asset: `./assets/badges/copy-4.png`.

### Punctuation

Do not use periods, question marks, or exclamation points in badge copy. Badges are meant to be instantly scannable status indicators.

> **Historical figure 19 — source figure reference (only approved samples, if any, are linked below):** Copy 3. Source asset: `./assets/badges/copy-3.png`.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: copy-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/copy-2.png)

- [copy-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/copy-2.png) — exact source blob `82aba4a41e3b` (illustrated above)
- [copy-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/copy-3.png) — exact source blob `a26678996b03`
- [copy-4.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/copy-4.png) — exact source blob `5031657e0c2f`
- [iconography-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/iconography-1.png) — exact source blob `7d27b9022fb2`
- [placement-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/placement-2.png) — exact source blob `49c611757adf`
- [placement-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/placement-3.png) — exact source blob `1500b8ee342b`
- [score-to-status-mapping-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/score-to-status-mapping-2.png) — exact source blob `022556b25972`
- [states-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/states-1.png) — exact source blob `e2a4b05a492b`
- [states-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/states-2.png) — exact source blob `335d22ac8863`
- [states-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/states-3.png) — exact source blob `c7d2163fd862`
- [states-5.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/states-5.png) — exact source blob `745b0c119a83`
- [variants-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/variants-1.png) — exact source blob `475fa87603a9`
- [variants-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/variants-2.png) — exact source blob `81d683c9732a`
- [variants-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/variants-3.png) — exact source blob `f2bebe7be6c8`
- [variants-4.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/variants-4.png) — exact source blob `79aaadf6d27e`
- [variants-5.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/variants-5.png) — exact source blob `8815941abb7e`
- [variants-6.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/badges/variants-6.png) — exact source blob `d61cb1b03399`
