> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/surfaces-and-elevations.mdx`, Git blob `1231393bcf0ddff3618e3a1c01438bc14bb779ff`; 15 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Historical upstream diagram of layered backgrounds and shadows; not the HSK AI app color palette or component styling. Source asset: `./assets/surfaces-and-elevations/surfaces-and-elevations.png`.

# Surfaces and elevations

Surfaces are background colors. Elevations are shadows. Both are separate decisions that work together to define the spatial relationships users navigate — surfaces differentiate regions, elevations communicate depth.

> **HSK AI implementation boundary (verified in code):** The iPhone PWA course uses `app/static/course_v3_data/design-tokens.css` (`--hsk-paper`, `--hsk-paper-raised`, `--hsk-card-surface`, `--hsk-divider`, theme-aware values), `app/static/course-v3.html` (safe-area-aware `.wrap`, `.scr`, `.nav`, `.sheet`), and the independently styled `app/static/iphone-pwa-voice.html`. The Android `LessonCharacters.kt` routes real lesson-card types to approved characters. The diagrams below are **professional concepts from a historical external design system**, not existing HSK UI, released components, valid HSK shadow tokens, or instructions to replace that behavior. Preserve verified platform behavior, accessibility, backend contracts and official HSK AI semantic color meanings; the current component shape, surface depth and styling are an implementation baseline, **not** a veto on the professional visual target. Do not import original school colors, Wonder Blocks classes, desktop layout, or branded imagery into production.

**Professional-first HSK AI visual hierarchy:** the existing `.agents/skills/hsk-ai-ui/SKILL.md` documents a current preference for flat settings/navigation/list rows, no unnecessary icon backplates or nested cards, one primary action per context and >=44 CSS px PWA / >=48 dp Android touch targets. These functional/accessibility constraints remain, but current card geometry, surface arrangement and visual emphasis may be improved to meet the stronger professional component standard. Elevation is an optional supporting cue, **not** a default for every selected card, icon, lesson or CTA. Maintain layout-matched skeleton slots, keyboard visibility and reduced-motion alternatives.

**Related distinction:** a page/task *surface* supports one continuous workflow; a *Card* groups a discrete comparable item. Do not replace the current lesson workspace with a generic elevated Card based only on its appearance. The archived source committee's decisions do not govern HSK AI.

## Principles

    
- **Elevation should reflect a real spatial relationship** (Purposeful): A component deserves higher elevation when it genuinely sits above other content — covering it, interrupting it, or pinning above it. If a component isn't doing any of those things, it doesn't need more elevation.

    
- **Predictability is what makes the system trustworthy** (Consistent): Users read elevation cues automatically. When the same component type always sits at the same level, those cues become reliable — inconsistency erodes the signal until users stop noticing it at all.

## Surfaces

The historical illustrations show two conceptual layers, **not** a rule that HSK AI has exactly two color values. Actual HSK AI course tokens vary by current theme; the separate Voice screen has its own verified dark visual language.

| HSK AI role in the existing course | Verified token/source |
| --- | --- |
| Page / main reading background | `--hsk-paper` |
| Raised content background | `--hsk-paper-raised` |
| Lesson card / supporting surface | `--hsk-card-surface` |
| Outline / divider | `--hsk-divider` |
| Dimmed content behind course modal bottom sheet | `app/static/course-v3.html` `.sheet` uses `rgba(20,17,13,.5)` (screen-specific CSS, **not** a shared semantic token) |

Do not treat the source-specific `semanticColor.core.*` identifiers or the figures' palette as HSK AI's official design tokens.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Swatches for Surface 1 - Subtle, Surface 2 - Default, and Surface scrim. Source asset: `./assets/surfaces-and-elevations/surfaces-overview.png`.

### Surface 1

The main page background — the paint on the wall. Everything else sits in front of it. Nothing is behind it. It also works for supplementary cards that carry secondary information and don't need to assert themselves visually. A border alone defines their edge.

Use for: page and screen backgrounds, full-bleed layout regions like sidebars and headers, and supplementary cards where a border is sufficient to define the boundary.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Mockup of a page with a sidebar and cards on the Surface 1 background — Page backgrounds are set to Surface 1. Other containers that are not the main priority of a page can also have Surface 1 background color.. Source asset: `./assets/surfaces-and-elevations/surface-1.png`.

### Surface 2

The first layer on the wall. Elements using Surface 2 sit closer to the user than the background — distinct objects in front of the page, not part of it. Surface 2 is also where the primary interaction happens. In a practice exercise, this is the surface a learner answers a question on — the most important element in the view, and the one demanding their attention and input.

Use for: primary content cards, content panels, modals, drawers, and components that need to read as the focal object on the page background.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Mockup of a content card standing out as the focal object on the page — Containers that are the main focus of the page have a Surface 2 background color.. Source asset: `./assets/surfaces-and-elevations/surface-2.png`.

### Surface scrim

A semi-transparent overlay applied over the page when a modal or drawer is open. The scrim signals that the content beneath is behind and unavailable while the overlay requires attention.

Use a scrim when the **existing** overlay actually places the rest of the screen into a modal or blocked state. In the course, the `.sheet` overlay has a dimmed background; AI Voice has its own verified `.sheetLayer`/`.scrim` behavior. An anchored non-modal popover is different. Do not inherit a source-exclusive token or blindly alter functional overlay flows. **Retain the professional scrim, elevation, separation, focus and modality details** as the target for redesign.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Mockup of an open drawer with a scrim dimming the page content behind it — A drawer is open above the page; the scrim dims the page content behind it while the drawer requires attention.. Source asset: `./assets/surfaces-and-elevations/surface-scrim.png`.

## Elevation

The following four levels are a **reference-only visual vocabulary**, not four shipped HSK AI elevation tokens. The inspected PWA `design-tokens.css` does not define `boxShadow.low/mid/high` or `semanticColor.core.shadow.*`. Any shadow must be sourced from the actual owning screen/component and checked in its supported themes.

| Illustrative level | Professional purpose | HSK AI decision |
| --- | --- | --- |
| Base | Flush region with no extra shadow | Prefer the professional surface treatment; a current screen can be kept only if it already satisfies the target hierarchy |
| Low | Slight visual separation | Use when the professional visual hierarchy warrants separation; implement through verified roles or explicitly propose a new token instead of inventing an existing `boxShadow.low` |
| Mid | Temporarily floating but non-modal help | Preserve supported HSK AI popover anchoring and keyboard behavior |
| High | Modal overlay and major interruption | Preserve the existing overlay layering, not upstream shadow constants |

Original diagrams retain their own shadows and swatches for **analysis only**; they do not specify HSK AI values.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** Swatches for the four elevation levels: Base, Low, Mid, and High. Source asset: `./assets/surfaces-and-elevations/elevation-overview.png`.

### Base

For components that sit flush with the surface. The right choice when the element is already the clear focus of the page, or when the component communicates interactivity through other means — buttons, tabs, checkboxes, list items, and inputs all use color, border, and hover states to signal affordance. Shadow on these would be overkill.

Use for: static containers, layout elements, and interactive components that communicate affordance through other means.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** Mockup of a card at base elevation, flush with the surface with no shadow — The card contains multiple interactive elements and the content here is already the main focus of the page. Adding shadow to it would add depth without adding meaning.. Source asset: `./assets/surfaces-and-elevations/elevation-base.png`.

### Low

For components where a subtle lift signals that the whole thing is a discrete, prominent unit — not just a region of the page. The shadow makes the card feel tangible and foregrounded, whether the entire surface is interactive or it simply contains the primary action on the page. For stateful components like accordions, apply elevation only when expanded. A collapsed card is passive — elevation would imply prominence before the user has engaged with it.

Use for: content cards that function as primary focus or selectable units, and expanded accordion panels.

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** Mockup of a card lifted off the surface with a subtle low-elevation shadow — The shadow signals that this is a main priority of the page and that the whole card is a selectable unit, not just a region of the page.. Source asset: `./assets/surfaces-and-elevations/elevation-low.png`.

### Mid

For popovers. Temporary surfaces that appear above the main page flow without blocking it.

Use for: popovers and tooltips.

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** Mockup of a popover floating above the page at mid elevation — The popover floats above the page content without blocking it — the stronger shadow is what separates it from the layer beneath.. Source asset: `./assets/surfaces-and-elevations/elevation-mid.png`.

### High

For components that must command full attention and interrupt the user's flow.

Illustrates toasts and modals in the upstream system; **do not require a strong shadow or interruption** for every HSK AI toast. Existing notification and modal behavior takes precedence.

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** Mockup of a toast floating clearly above all page content at high elevation — Since toasts are temporary, urgent, and demand immediate attention, a strong shadow ensures they're never visually lost or confused with page content beneath them.. Source asset: `./assets/surfaces-and-elevations/elevation-high.png`.

## Using surfaces and elevations together

Surfaces and elevations are independent — either can be applied without the other — but they're often used in combination. An upstream example card uses a differentiated surface and subtle shadow together: the surface color distinguishes the card from the page background laterally, and the shadow establishes its perceived depth. Not every surface needs elevation, and not every elevated component needs a distinct surface color. The test is always whether the combination is communicating something real to the user or just adding visual complexity.

| Component | Surface | Elevation |
| --- | --- | --- |
| Existing HSK UI concept | Surface decision | Depth decision |
| --- | --- | --- |
| Course page | `--hsk-paper` | Current page CSS, not an inherited `Base` token |
| Raised content | `--hsk-paper-raised` or `--hsk-card-surface` when actually used | Match the professional surface hierarchy, mapped to real existing or explicitly proposed roles |
| Lesson/choice item | Verified course styles | Preserve answer feedback and focus |
| Anchored help | Actual popover styling if implemented | Not necessarily modal; avoid covering the keyboard |
| Bottom sheet / modal | Actual `.sheet` / Voice-specific overlay CSS | Preserve existing scrim, stacking, focus and dismissal |
| Voice Orb | Its own red pearlescent screen and renderer | Never re-skin via generic cards/shadow tiers |

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** Two stacked-layer diagrams showing how surfaces and elevations combine, from the background at Surface 1 with base elevation up to alerts and modals at Surface 2 with high elevation. Source asset: `./assets/surfaces-and-elevations/combinations.png`.

## Usage guidelines

### Base layer should not falsely imply interactivity

A background should remain visually subordinate to the current learning task. This is a hierarchy principle, **not** a claim that the real app implements the original system's Surface 1/Surface 2 classes. Preserve actual task/overlay layering semantics, but elevate the visual system to the professional surface/elevation hierarchy in the later redesign; avoid redundant depth effects.

> **Historical figure 12 — source figure reference (only approved samples, if any, are linked below):** A Surface 1 card sitting flat on the page with no shadow, labeled Surface 1 + Elevation: Base. Source asset: `./assets/surfaces-and-elevations/usage-surface-base.png`.

### Elevation is a page-level decision

Before reaching for Low elevation, look at the full page. On a complex page — a practice view with chat, action buttons, and a question all present — Low elevation gives the question card the hierarchy it needs to read as the primary focus. On a simpler page where the main content is already uncontested, Base is sufficient. Adding Low where nothing is competing creates depth without meaning.

> **Historical figure 13 — source figure reference (only approved samples, if any, are linked below):** A white Surface 2 card sitting on a Surface 1 background with a soft shadow, labeled Elevation: Low. Source asset: `./assets/surfaces-and-elevations/usage-page-level.png`.

### Elevation low is for interactive components at rest — not on hover

In the upstream example, Low is the default elevation rather than a hover state. This is **not** a binding HSK AI shadow level. Interactive states are handled by the component's state tokens, not by increasing elevation level. Don't increase elevation on hover unless the component's design explicitly uses elevation as a state signal.

> **Historical figure 14 — source figure reference (only approved samples, if any, are linked below):** Mockup of interactive cards at low elevation, one showing a hover cursor — increase elevation on hover. Use state tokens to handle interactive states instead.. Type: dont. Source asset: `./assets/surfaces-and-elevations/usage-low-at-rest-v3.png`.

### Scrims belong with elevation high

Use a scrim for truly **modal** content when the existing screen blocks interaction with the rest of the page. Do not reclassify non-modal HSK AI helpers as modal or replace the existing course and AI Voice overlay mechanisms merely to fit the source diagram. Test dismissal, safe areas, keyboard, focus restoration and screen-reader behavior in the actual PWA/Android component.

> **Historical figure 15 — source figure reference (only approved samples, if any, are linked below):** A modal dialog at high elevation paired with a scrim dimming the page behind it. Source asset: `./assets/surfaces-and-elevations/usage-scrim-high.png`.

## Accessibility

### Shadow alone is not enough

Users with low vision, in high-contrast mode, or on poorly calibrated displays may not perceive shadow. Surface color must communicate boundaries without relying on shadow, and text on Surface 2 must meet WCAG contrast requirements against that background — not just against Surface 1.

### Elevation does not replace focus rings

A component that appears elevated does not have an inherent focus state. Focus rings are required on all interactive elements regardless of their elevation level. Never suppress a focus ring because the component "already looks distinct."

### Modal dialogs must trap and restore focus

Components using High elevation that create a modal context must trap keyboard focus within the overlay — focus must not be reachable on the dimmed content underneath. When the modal closes, focus must return to the element that opened it.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: combinations.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/combinations.png)

- [combinations.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/combinations.png) — exact source blob `bf3ea8721306` (illustrated above)
- [elevation-base.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/elevation-base.png) — exact source blob `30a30daab149`
- [elevation-high.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/elevation-high.png) — exact source blob `175888054877`
- [elevation-low.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/elevation-low.png) — exact source blob `7ff1292d3aa7`
- [elevation-mid.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/elevation-mid.png) — exact source blob `bbb57cb47b6c`
- [elevation-overview.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/elevation-overview.png) — exact source blob `c15ed7290e56`
- [surface-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/surface-1.png) — exact source blob `319f7b300ac3`
- [surface-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/surface-2.png) — exact source blob `c1820c2cd73d`
- [surface-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/surface-3.png) — exact source blob `11173ef26602`
- [surface-scrim.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/surface-scrim.png) — exact source blob `68bb024a04d5`
- [surfaces-and-elevations.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/surfaces-and-elevations.png) — exact source blob `f8ade7d17c55`
- [surfaces-overview.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/surfaces-overview.png) — exact source blob `c3cf49e2f166`
- [usage-low-at-rest-v3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/usage-low-at-rest-v3.png) — exact source blob `48fa93500c26`
- [usage-page-level.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/usage-page-level.png) — exact source blob `4e6eddb8a04b`
- [usage-scrim-high.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/usage-scrim-high.png) — exact source blob `b8c66b8a0da7`
- [usage-surface-base.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/surfaces-and-elevations/usage-surface-base.png) — exact source blob `e5a1d82e4e2e`
