> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/colors.mdx`, Git blob `3ac38839501ffc9324d224b07329ffc4622e7488`; 4 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# Colors

HSK AI uses **semantic colors** to make lesson content readable, support correct and incorrect answers, show actual progress and keep navigation clear. Colors express **purpose**, not decorative preferences. The actual PWA tokens and Android palette are the **inventory of implemented roles**, not a ceiling on professional semantic palette design. Preserve brand identity and verified state meaning while refining any inferior contrast, hierarchy or color application in the later UI/UX phase.

Read the [HSK AI semantic color tokens](colors-semantic.md) page for existing token names, verified light/dark values, contrast and state rules.

## Principles

### Color supports meaning, never carries it alone

A correct response needs a clear success state plus text, shape/icon or existing character reaction. An incorrect response needs unambiguous correction feedback. Payment success, score, lesson completion and Pro entitlement must **not** be communicated as accomplished until confirmed by the authoritative state.

### Purpose before color

- **Primary/brand:** use existing product accent roles such as `--hsk-cinnabar` for non-destructive interactive emphasis.
- **Content:** use `--hsk-ink` and secondary text on the actual current background.
- **Success:** use the established Jade family where a verified positive state is appropriate.
- **Warning/errors:** do **not** misuse the brand's light-theme red as a generic error; where needed, use the actual screen's validated error presentation and propose a dedicated role when the existing tokens do not provide one.
- **Milestone/Pro:** use the existing Gold family only when its associated state or verified event exists.
- **Decorative graphics:** preserve the canonical Panda/side characters and AI Voice Orb independent of generic interface-color conventions.

### Respect light and dark themes

The existing `--hsk-cinnabar` role is `#E04A40` on the light theme and **`#20BCEB` on the dark theme**. Do not paint all non-destructive buttons red regardless of theme. Re-evaluate text foreground contrast, accessibility and correct/incorrect signals in both.

### Readable contrast

For WCAG AA, normal text usually needs **4.5:1**, large text or essential non-text UI boundaries **3:1** against their real background. Do not assume a palette is accessible merely because a pair uses a semantic variable; check the actual rendered combination, including overlays and focus states.

## Source reference: palette, tokens and accessibility

The four images in this section are **original design-method references**, not HSK AI palette samples, screenshots, permitted colors or token names. They remain because the underlying professional method is valuable.

### Primitive palette versus semantic meaning

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Historical source design color overview: an example of visual hierarchy, not HSK AI brand colors. Source asset: `./assets/colors/colors.png`.

The source overview demonstrates visual restraint: use a small, intentional accent family and distinguish content, actions and feedback. For HSK AI the actual brand roles and dark-theme variants in the production app remain authoritative.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Reference grid demonstrating a primitive color palette; its particular hues are not HSK AI tokens. Source asset: `./assets/colors/primitives-grid.png`.

**Primitives** are raw shades. They should inform semantic decisions, not be pasted directly as hex values throughout an interface. When considering a new HSK AI color, first identify its function, compare it against existing light/dark roles, and test the contrast of foreground, background and state indicators.

### Semantic color roles

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Reference example of mapping raw colors to purposeful semantic tokens; the illustrated token names belong to the source library. Source asset: `./assets/colors/semantic-tokens.png`.

The transferable principle is **intent over appearance**. Apply actual HSK AI names such as `--hsk-ink`, `--hsk-paper`, `--hsk-divider`, `--hsk-cinnabar` and `--hsk-jade` where verified. Never create nonexistent HSK AI warning or critical tokens merely to imitate the reference. A destructive action, a wrong lesson answer, a payment failure and a brand accent are distinct concepts.

### Accessible pairings

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Professional reference showing accessible foreground/background pairings; actual combinations must be checked against HSK AI themes. Source asset: `./assets/colors/accessible-pairings.png`.

- Test **4.5:1 for normal text** and **3:1 for qualifying large text and essential non-text interface boundaries** against the **rendered** HSK AI background. Bigger fonts do not automatically make low contrast acceptable.
- Decorative figures need not act as state signals; important status graphics, focus boundaries and selected options must be discernible without relying on hue alone.
- A subtle border is acceptable only where it is not the sole signifier of a necessary boundary. A focus ring and critical form control boundary need the contrast required by their role.
- When layers or overlays change the underlying background, measure the effective visible colors, not just standalone tokens.
- Pair positive/negative lesson colors with a shape, readable message and the actual character reaction. Check theme switching and color-vision differences.

### Decision checklist for a new color

1. Which real semantic product role does it express?
2. What existing app token or Android role already covers that intent?
3. Is it distinguishable from verified error, success, pending, disabled and ordinary brand action?
4. Does it remain legible in light, dark and overlaid states?
5. Is the outcome verified by the server where relevant?
6. Is the chosen color supplemented with a non-color cue?

## HSK AI implementation guidance

**Existing sources:**
- PWA: `app/static/course_v3_data/design-tokens.css`.
- Android: `android/app/src/main/java/com/pomp/hskai/core/design/Color.kt` and Material color scheme defined in `Theme.kt`.

Use current semantic role names and token mappings. An experimental palette, unverified UI theme or additional global color must be proposed and tested rather than imported from a source screenshot. Avoid hard-coded source-brand colors, invented gem economy states and school-specific score thresholds.

**Hanzi/pinyin/translation** remain readable in every learner exercise, and important text may never be hidden by an overlay or made illegible by reduced contrast. Use icon and readable message with state colors, never color alone.

## Review checklist

1. Does the color match the verified learning or UI state?
2. Does its meaning survive grayscale, reduced motion and screen reader use?
3. Is the contrast sufficient on both themes at the actual size/weight?
4. Does the current PWA token or Android role really exist?
5. Would the change preserve approved Panda/other character colors and the red Voice Orb?
6. Have small screens, large text, overlays and keyboard states been checked?

## Scope

This page is **HSK AI-only design guidance**. It does not authorize editing the production app or replacing Storybook's temporary authoring dependencies without separate validation.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: accessible-pairings.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/colors/accessible-pairings.png)

- [accessible-pairings.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/colors/accessible-pairings.png) — exact source blob `56a16cea4c3e` (illustrated above)
- [colors.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/colors/colors.png) — exact source blob `df78d2ee0036`
- [primitives-grid.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/colors/primitives-grid.png) — exact source blob `2f75a0291c64`
- [semantic-tokens-hero.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/colors/semantic-tokens-hero.png) — exact source blob `b3b925f81f2c`
- [semantic-tokens.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/colors/semantic-tokens.png) — exact source blob `2266c0c3d6a5`
