> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/toggle.mdx`, Git blob `d61a6b139a598074bafb5e994f2d72281bef1830`; 11 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Toggle. Source asset: `./assets/toggle/toggle.png`.

# Toggle

> **HSK AI adaptation:** Original source images show filtering and preferences, not HSK AI settings. Reuse the binary-control and filtering mechanics only where the PWA/Android feature actually exists. A preference requiring OS permission, a server write, or a reversible off state must **not** be declared saved until its real outcome is known. Preserve the source's difference between an immediate filter toggle and a deferred filter-modal selection.

*Component role: Binary/Boolean control*
 A simple on/off mechanism used for a quick, either-or choice — filtering results by a single boolean attribute, or switching a setting or preference on and off.

## Recommended: When to use

The choice to use a toggle is determined by the need for an immediate, singular action on a single boolean attribute.

| Use when | Example use |
| --- | --- |
| The choice is strictly binary | On/Off, Include/Exclude, True/False |
| The action takes effect immediately without confirmation | A supported "completed only" list toggle may immediately filter the visible results; a real HSK AI setting takes effect according to its verified save and device-permission rules. A toggle inside a filter modal remains pending until Apply — see [Filter modal](#filter-modal) under Filtering. |
| The state is always visible and needs to be persistent | A global constraint that remains active across the session until the user turns it off or clears filters; a notification preference that stays set until changed in account settings |

## Avoid: When NOT to use

| Don't use when | Recommended alternative | Rationale |
| --- | --- | --- |
| There are 3 or more possible states | Checkbox group | Toggles are only appropriate for binary decisions. More states need a different selection pattern. |
| Multiple options can be selected at the same time | Checkbox group | Toggles act on a single attribute. Selecting multiple options at once — whether additive filtering or enabling several related settings — requires checkboxes. |
| The action requires an Apply button to commit | Checkbox or form input + apply button | Toggles activate immediately. If the user needs to review before confirming, the pattern breaks. Exception: filter modal — see Filtering. |

## Filtering

### Placement

A filter toggle can sit in the filter bar or inside the More filters modal.

In the filter bar, place the toggle after primary filters (like Date or Course). This positions it as a high-level global constraint applied after the core dimensions have been selected.
Never place a toggle before dropdowns or inline within a list of results.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Placement. Source asset: `./assets/toggle/placement.png`.

Only one toggle should be visible in the filter bar at a time. If additional boolean filters are needed, they belong inside the filter modal accessed via "More filters." For how a toggle behaves once it is there, see [Filter modal](#filter-modal).

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Multiple toggles grouped under Display options inside the More filters modal — multiple toggles grouped inside "More filters" modal. Type: do. Source asset: `./assets/toggle/interaction-2-do.png`.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Multiple toggles exposed directly in the filter bar — multiple toggles exposed directly in the filter bar. Type: dont. Source asset: `./assets/toggle/interaction-2-dont.png`.

### No filter chips

Toggles do not generate filter chips in the filter bar. Because the toggle is always visible and explicit in the UI, a chip would be redundant.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** A filter bar where an active toggle has incorrectly generated a filter chip — toggle state should not appear as a chip. Type: dont. Source asset: `./assets/toggle/interaction-1.png`.

### Clear all filters

An on toggle is an active constraint on the data even though it generates no filter chip. It activates the Clear filters button, and selecting Clear filters turns the toggle off.

Generating no chip is a display rule, not an exemption from the reset. The toggle's own visible state is what stands in for a chip — either the toggle itself in view, or the count indicator on the "More filters" button when it sits inside the modal. The constraint it applies is as real as any chip's, so a user clearing the view expects it gone.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** A filter bar with a Show only completed tasks toggle switched on and no filter chips below it, with the Clear filters button present because the toggle is active. Source asset: `./assets/toggle/clear-filters.png`.

### Filter modal

When a toggle lives inside a filter modal, it does not apply immediately. The effect is deferred until the user applies the modal filters. This is the only context where a toggle does not produce an instant result.
Inside a filter modal, the label sits to the left of the toggle, not inline to the right as it does in the filter bar. An optional short description can sit below the label to add context when the toggle's purpose isn't self-evident from the label alone.

A toggle inside a filter modal ships off. Nothing in the More filters modal should be pre-applied — a filter the user did not choose, sitting behind a button, narrows the data with nothing on screen to say so.

When the user turns a modal toggle on and applies, it counts toward the numeric badge on the More filters button. With no chip and the modal closed, the badge is the only signal that the toggle is on.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** A filter bar with a numeric badge on the More filters button and no filter chips below, with the Clear all filters button present because a modal toggle is applied — display an applied modal toggle as a badge count, not as an active filter chip.. Type: do. Source asset: `./assets/toggle/filter-modal-badge.png`.

### Copy

The label must always be visible next to the toggle. It should clearly communicate what happens when the toggle is on — not what state it is in. Keep labels concise and action-oriented, describing the effect (e.g., "Show only completed tasks"). Avoid vague words like "Filter" or labels that describe the off state.

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** Copy. Source asset: `./assets/toggle/copy.png`.

## Preferences

### Placement

The toggle sits to the left of its label, with the label inline to the right — the same order as the filter bar, and the reverse of the filter modal, where the label sits to the left of the toggle.

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** Preferences placement. Source asset: `./assets/toggle/preferences-placement.png`.

### Instant save

Preference toggles save instantly on change. There is no deferred or confirm step — unlike the filter modal exception in Filtering, every preference toggle takes effect immediately.

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** Preferences interaction. Source asset: `./assets/toggle/preferences-interaction.png`.

### Copy

The label names the actual supported setting as a concise noun phrase (e.g., "Notifications" only when that notification preference exists), not an unrelated messaging or classroom-management feature. Avoid imperative phrases such as "Enable notifications" when the label should name the preference. Clearly distinguish saved preference, pending permission and unavailable state.

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** Two preference toggles compared: “New assignment notifications” marked with a green check, and “Enable new assignment notifications” marked with a red cross. Source asset: `./assets/toggle/preferences-copy.png`.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toggle/copy.png)

- [copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toggle/copy.png) — exact source blob `a3b7cd033a43` (illustrated above)
- [interaction-2-do.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toggle/interaction-2-do.png) — exact source blob `dec7918bf0f8`
- [interaction-2-dont.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toggle/interaction-2-dont.png) — exact source blob `a60e7af2a13f`
- [placement.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toggle/placement.png) — exact source blob `7fbcd4e0ddd1`
- [preferences-copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toggle/preferences-copy.png) — exact source blob `e72822c18f62`
- [toggle.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/toggle/toggle.png) — exact source blob `1a58fbe0d81c`
