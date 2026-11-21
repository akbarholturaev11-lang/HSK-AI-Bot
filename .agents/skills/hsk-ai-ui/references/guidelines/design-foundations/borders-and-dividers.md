> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/borders-and-dividers.mdx`, Git blob `ef78fa529411b0fba3ab8d7e20a8009aa27c94af`; 12 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# Borders and dividers

Borders clarify where a control or surface begins. Dividers separate adjacent content without creating additional visual noise. For HSK AI, use **real mobile app tokens and platform components**, not names or focus packages from another UI framework.

## Principles

1. **Use the lightest tool that works:** grouping and spacing first, then dividers, then a full border when the boundary matters.
2. **Keep a consistent hierarchy:** the same interaction/state should not have a different border system on each phone screen.
3. **Show action and state clearly:** a selected option must remain identifiable without relying only on a color change.
4. **Do not disguise missing information:** an error needs a real explanation and recovery route, not a red border alone.

## HSK AI existing tokens

The PWA defines `--hsk-divider` as `#EAE0CC` in the light theme and `#17617D` in dark mode. These values are **existing divider colors**, not a verified 3:1 focus treatment. Other border and focus colors must be chosen from the real current HSK AI screen and checked visually; do **not** fabricate a `semanticColor.core.border.*` token or assume it exists in the HSK AI app.

Android has its own `PompColors` palette and Material 3 roles. Keep the same meaning, but let native components use correct accessible focus, pressed, selected and disabled states rather than trying to inject PWA CSS geometry into Kotlin.

## When to use a border

- A card or other grouping needs a visible edge to be distinguished from its actual surrounding surface.
- A text input, selectable row or custom control requires a clear boundary to be discoverable.
- A focused interactive control needs **high-contrast focus treatment** that does not disappear in dark mode.
- An error input needs a state border **plus** an explanation; never use border color as the sole failure cue.

Follow the **professional border/divider hierarchy** for real controls, cards, focus and selection, preserving source-grounded geometry and visual intent. Treat current component widths/radii as an implementation inventory, not an aesthetic veto; map the target onto actual HSK AI theme roles or propose new roles without fabricating already-implemented tokens.

## When to use a divider

- Between dense, actual data-table rows when the separation helps scanning.
- Between a fixed dialog header/footer and its scrolling content.
- Between distinct filter groups or neighboring records within a common container.
- Not when an ordinary heading or adequate spacing already makes sections clear.

Use `--hsk-divider` or the corresponding native theme role rather than a copied line color from a design screenshot.

## Bordered choices versus line-divided lists

| Bordered option cards | Line-divided list |
| --- | --- |
| Short, curated and mutually exclusive selection | Browsable or searchable selection |
| Each option must be independently identifiable | The parent list container already defines the outside edge |
| No substantial filtering needed | A genuine supported filter/search may narrow the options |
| Useful for a supported HSK track/level choice if already present | Useful for supported lesson or result lists if already present |

Never build fictional class selection, teacher/roster forms or school filters to populate a demonstration. Preserve the **professional component composition** and distinguish a true card from a continuous task surface. Do not force a card solely because a source image depicted one, and do not freeze inferior current HSK AI borders/shapes in the future redesign.

## Focus, error and accessibility

- **Focus must be visible**, keyboard and assistive-technology friendly and distinguishable against adjacent colors (typically at least 3:1 for applicable graphical indicator contrast). Do not suppress native focus behavior or replace it with an untested border.
- Input errors require a concise localized message, a non-color cue and clear recovery. A wrong exercise answer is a learning state, not necessarily a broken input.
- Disabled is different from read-only, selected, pending and error. Each has its own meaning and appropriate visual treatment.
- Dividers are structural, not buttons; do not render them as interactive targets.
- Use 44 CSS px minimum iPhone PWA touch targets and 48 dp native Android targets where relevant, even if a border or icon is visually much smaller.
- Verify text scaling, Hanzi strokes/pinyin tone marks, light/dark surfaces, keyboard overlay and reduced-motion interactions on real mobile screens.

## Original professional examples, adapted by function

The following figures restore the **original detailed border and divider examples**. Their blue/neutral palette, classroom content and source component tokens are reference screenshots only; **do not copy them into HSK AI themes**. The current `--hsk-divider`, actual PWA focus treatment and native Android components **document the present implementation**; the professional border/focus distinction remains the target for future value and geometry improvements.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Original border and divider overview; educational diagram rather than HSK AI app screen. Source asset: `./assets/borders-and-dividers/header.png`.

### Border intensity and contrast

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Two source reference border strengths shown side by side. Source asset: `./assets/borders-and-dividers/border-colors.png`.

- **Subtle border:** appropriate when the shape is already clear through readable text, spacing, surface or elevation. It need not itself carry a state or interactive boundary. Ask: *If the line disappeared, would the learner still identify the control?*
- **Default/discoverable border:** required when the line itself is the primary cue that an input or action has an edge. In this case verify non-text contrast, normally 3:1 where applicable.
- Border thickness is part of component behavior: do not change the size of a selectable card merely to show focus. The original reference library used 1px normally and sometimes 2px for focus; **those are source examples, not fixed HSK CSS/Android dp instructions**.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Reference showing cards with light, nonessential borders. Source asset: `./assets/borders-and-dividers/subtle-border.png`.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Reference of a discoverable text input whose edge is a primary affordance. Source asset: `./assets/borders-and-dividers/default-border.png`.

### Focus state must be distinct

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Reference dropdown with a visible focus indicator. Source asset: `./assets/borders-and-dividers/focus-border.png`.

A keyboard-focused action requires visible, accessible focus without surprising layout shift. Use each platform's **actual supported focus implementation**. Never import Khan's Wonder Blocks focus package into the HSK AI application. Check light/dark contrast and visible focus against adjacent error/selected borders.

### Selected, invalid and disabled

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** Source comparison of selected, focused, invalid and disabled text-field borders. Source asset: `./assets/borders-and-dividers/state-inputs.png`.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** Source example of a selected choice card with a distinct outline. Source asset: `./assets/borders-and-dividers/state-card.png`.

Selected, pending, invalid, disabled and read-only are **different states**. Error requires text and recovery, not just a red line; a wrong quiz answer is a learning result, not necessarily an invalid form input. In a selectable card, retain an accessible checked/selected cue (text, icon, radio state) in addition to the outline.

### Table, modal and section dividers

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** Source data table with horizontal separators; the displayed data are illustrative, not HSK AI learner records. Source asset: `./assets/borders-and-dividers/table-dividers.png`.

Use row separators as a restrained default for dense data. Don't mix a full cell grid, zebra stripes and horizontal lines without a specific measured scanning benefit. Preserve cell/column association and focus in an accessible HSK AI admin table.

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** Reference of modal boundaries separating fixed header/footer from scrolling content. Source asset: `./assets/borders-and-dividers/header-footer-dividers.png`.

A modal's fixed header/footer can need a clear line between stationary actions and scrolling content, especially with the on-screen keyboard and safe areas. Preserve primary actions and unsaved learner input.

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** Source reference separating independent content groups inside a dialog. Source asset: `./assets/borders-and-dividers/section-dividers.png`.

For independent filter groups, a section line can clarify scope; don't add dividers directly under every heading when spacing and labels already establish hierarchy.

### Bordered choice cells versus divided lists

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** Source example of separately bordered selectable cells; its original class names are not HSK AI options. Source asset: `./assets/borders-and-dividers/bordered-cells.png`.

- **Bordered cells:** a short fixed mutually exclusive choice on the page background (e.g., *an already supported HSK track/level choice*). Each target needs its own edge and a selected cue.
- **Line-divided list:** content already inside a container, especially when searching or filtering. Use rows and separators rather than a second full border around every record.

> **Historical figure 12 — source figure reference (only approved samples, if any, are linked below):** Reference list within a containing surface using lightweight horizontal row lines. Source asset: `./assets/borders-and-dividers/line-dividers.png`.

No image represents actual student/classroom functionality in HSK AI. These rules are about **visual organization**, not new product screens. The original source's main professional distinctions—subtle vs discoverable, focus vs selected, table vs section, and cells vs list—are now explicit for HSK AI.

## Restored edge and divider decision rules

### Pick the least intrusive boundary

- Start with **spacing**, then a **divider**, then a **full border** only when the boundary itself helps recognition or action. This preserves hierarchy without turning every lesson group into a grid.
- A **subtle border** may be suitable when the card edge is already evident through elevation/spacing and the line is not essential. An interactive input whose shape depends on its border needs an edge with the applicable **3:1** contrast, plus focus and error treatment.
- A **focus ring** must remain visible by keyboard, should not shift the control's layout, and must not be repurposed as the only indicator of selection or validation error.
- Source examples use roughly **1 CSS px** neutral strokes and stronger focus treatment. These are design-scale references, not a claim that every current Android/PWA control has identical dp/px geometry.

### Choose dividers by structural meaning

- **Table row separators:** consistently separate exact records; avoid mixing every-other-row shading, full grids and individual cell boxes without a measured comprehension benefit.
- **Header/footer dividers:** separate fixed modal and sticky navigation regions from independently scrolling content, respecting the PWA safe area and native Android inset.
- **Section dividers:** separate meaningfully different content areas. Do not insert a line automatically under every heading when heading typography and spacing already express the group.
- **Bordered choice cells:** appropriate for a small fixed list of independently selectable options on the page background.
- **Line-divided lists:** appropriate for already-contained, searchable or filterable items where each row is a distinct target.

### Error, selected and inaccessible states

- An invalid field must pair a distinct border with a readable inline message; a selected option needs a clear persistent state; a disabled control must be semantically disabled, not merely faded.
- Keep meaningful focus, selected, error and disabled borders distinguishable **in both light and dark themes** without importing the source product's blue or other raw semantic tokens.
- A decorative divider should not be focusable or look like a click target. Screen readers should hear row headings, labels and available actions rather than visual strokes.

## Implementation boundary

This is HSK AI-specific design guidance. It deliberately excludes foreign UI-library token paths, desktop classroom screenshots and third-party focus-package requirements. It changes no production CSS, native component or navigation behavior.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: border-colors.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/border-colors.png)

- [border-colors.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/border-colors.png) — exact source blob `be1650382fcd` (illustrated above)
- [default-border.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/default-border.png) — exact source blob `4b8dc5814863`
- [focus-border.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/focus-border.png) — exact source blob `0c1640d3d5d5`
- [header-footer-dividers.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/header-footer-dividers.png) — exact source blob `f10597a24943`
- [header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/header.png) — exact source blob `3909df7c7627`
- [section-dividers.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/section-dividers.png) — exact source blob `4b0293962b09`
- [state-card.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/state-card.png) — exact source blob `c42d7d58c6e2`
- [state-inputs.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/state-inputs.png) — exact source blob `727448cdca54`
- [subtle-border.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/subtle-border.png) — exact source blob `39012be3b39f`
- [table-dividers.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/borders-and-dividers/table-dividers.png) — exact source blob `911d36c02f03`
