> **HSK AI professional design guideline — portable review copy.** Current implementation is not implied. Source `__docs__/design-components/checkbox-group.mdx` (Git blob `76a44cfc5b515190667aad82205448fc21dfa9c6`); 6 historic figure references, 0 MDX demo blocks. Approved neutral example PNGs are linked below where available; excluded foreign screens and vendor runtime code were not transferred. The original prose remains an internal source-derived draft. Full professional prose is retained as an internal source-derived draft.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Checkbox group. Source asset: `./assets/checkbox-group/checkbox-group.png`.

# Checkbox group

> **HSK AI adaptation:** Only available HSK AI options may be exposed as additive multi-select filters; do not invent categories. The app must provide real category values before showing a multi-select. Preserve the original **OR within a group / AND between distinct criteria**, immediate-versus-Apply timing and actual lesson titles (Hanzi and pinyin where they appear). These screenshots are source teaching examples only.

*Component role: Additive filtering/selectors*

A multi-selection mechanism that allows users to select multiple options from a single dimension simultaneously. Each selection adds to the filter — results matching any of the selected options are included.

## Recommended: When to use

The choice to use a checkbox group is based on the requirement for additive filtering — where multiple options from the same dimension can be true at the same time.

| Use when | Example use |
| --- | --- |
| Multiple options from the same dimension can apply simultaneously | Filtering by several available exercise categories as an **OR** choice, but only where an actual HSK AI view supports multi-select. |
| The selection is part of a form or larger filter context | Inside a filter modal where selections are confirmed with Apply — exposed directly or wrapped in a combobox depending on option count. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| Only one option can apply at a time | Radio buttons | Radio buttons clearly communicate mutually exclusive constraints — checkboxes imply multiple selections are valid. |
| The choice is binary or a single immediate global action | Toggle | A toggle is more appropriate for a single on/off action. Checkbox groups are primarily used for selection within a group. |

## Exposed or dropdown

- 8 or fewer — exposed by default.
- More than 8 — dropdown.
- Top filter bar — always a dropdown, regardless of count.

A dropdown is also acceptable at eight or fewer outside the filter bar — a settings page or a long form — where the group is one field among many and the user is setting a value they already know. Expose when seeing the options is part of the decision. Collapse when the user arrives knowing the answer and the surrounding form needs to stay scannable.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** A filter set with two exposed checkbox groups — Essay types with 3 options and Categories with 4 options — shown directly, not wrapped in a dropdown — 8 or fewer, exposed directly. Type: do. Source asset: `./assets/checkbox-group/placement-1.png`.

### Top filter bar

Horizontal space is constrained, so exposed groups would break the layout.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** A top filter bar where grade options are wrapped in a dropdown — top filter bar, always dropdown. Type: do. Source asset: `./assets/checkbox-group/placement-2.png`.

## Interaction

### Additive selection

Any number of options within the group can be selected simultaneously, including zero. Each selection adds to the active filter set — it does not replace previous selections.

Whether selections take effect immediately or wait for confirmation depends on where the group lives: exposed directly in a filter bar, selections apply as soon as they're checked; inside a combobox or filter modal, selections are held until the user presses Apply.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Interaction 1. Source asset: `./assets/checkbox-group/interaction-1.png`.

### Dropdown display

When used inside a multi-select dropdown, if a single selection is made the exact name of the selected item is displayed in the trigger, truncated with an ellipsis if needed.
If multiple selections are made, the trigger displays a count — for example, "4 selected."

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Interaction 2. Source asset: `./assets/checkbox-group/interaction-2.png`.

## Copy

What goes into an option label depends on where its content comes from.

**Category and filter labels:** When you're authoring the labels yourself (available exercise categories, learning-content types or other real criteria), keep them concise — a noun, a short noun phrase, or an adjective naming a type (Persuasive, Explanatory). Avoid full sentences or instructional phrasing. Labels should be parallel in structure — if one option is a noun, the rest should be too.

**Content titles:** When the option is a pre-existing piece of content (a lesson, quiz, or unit test name), use its actual title as-is. These aren't subject to the conciseness or parallel-structure rule above — they're inherited from the curriculum, not authored for the checkbox group, and shortening or rewording them would break their ability to identify the actual content.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** Copy. Source asset: `./assets/checkbox-group/copy.png`.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: checkbox-group.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/checkbox-group/checkbox-group.png)

- [checkbox-group.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/checkbox-group/checkbox-group.png) — exact source blob `d79160a70d7f` (illustrated above)
- [copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/checkbox-group/copy.png) — exact source blob `17d35ef83f57`
- [header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/checkbox-group/header.png) — exact source blob `80e4ce79e65f`
- [interaction-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/checkbox-group/interaction-1.png) — exact source blob `a085849e3c8d`
- [interaction-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/checkbox-group/interaction-2.png) — exact source blob `01c7dcbfdc00`
- [placement-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/checkbox-group/placement-1.png) — exact source blob `5ca856b288d5`
