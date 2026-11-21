> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/spacing.mdx`, Git blob `d062c6cbca2748f356b342ed3e234da8c2c5094f`; 7 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Spacing. Source asset: `./assets/spacing/spacing.png`.

# Spacing

Space is not the absence of content — it's content. The distance between two elements tells a user whether they belong together or apart, and whether a moment calls for focus or efficiency. Getting spacing right means reading context first, then choosing the value.

## Principles

    
- **Space defines belonging** (Relational): Proximity communicates relationship. Close together means related, further apart means separate. There is no neutral gap.

    
- **Density follows the task** (Contextual): The right amount of space depends on what the user is doing. Focused tasks need room to breathe; scanning tasks need information packed efficiently.

    
- **Repetition builds rhythm** (Consistent): When the same spacing is used for the same relationships throughout the product, structure becomes invisible — users feel the logic without noticing it. Inconsistent spacing makes structure visible as friction.

    
- **More is not always better** (Intentional): Generous spacing can feel calm and focused. It can also feel empty or slow. More space is not inherently better — it's appropriate or it isn't. The goal is never maximum space; it's the right amount for the context.

    
- **Space scales with the user** (Accessible): Spacing must remain usable when a learner zooms, increases text size, or changes display scaling. PWA uses its existing CSS spacing tokens and Android uses dp; both must be tested for wrapping, clipping, and target size rather than assuming fixed gaps automatically adapt to all accessibility settings.

## How the scale works

HSK AI uses its **existing shared 4-point spacing scale**: **4, 8, 12, 16, 24, 32, 48**. These are approved spacing steps, not a mandate to change every illustration dimension or typography metric. Do not impose a new `10px = 1rem` root-size convention; it is not the current HSK AI implementation.

| Step | PWA token (CSS) | PWA value | Android token (Compose) | Android value |
| --- | --- | --- | --- | --- |
| 1 | `--hsk-space-1` | 4px | `PompSpacing.XSmall` | 4.dp |
| 2 | `--hsk-space-2` | 8px | `PompSpacing.Small` | 8.dp |
| 3 | `--hsk-space-3` | 12px | `PompSpacing.Medium` | 12.dp |
| 4 | `--hsk-space-4` | 16px | `PompSpacing.Large` | 16.dp |
| 6 | `--hsk-space-6` | 24px | `PompSpacing.XLarge` | 24.dp |
| 8 | `--hsk-space-8` | 32px | `PompSpacing.XXLarge` | 32.dp |
| 12 | `--hsk-space-12` | 48px | `PompSpacing.XXXLarge` | 48.dp |

The production sources of truth are `app/static/course_v3_data/design-tokens.css` (PWA) and `android/app/src/main/java/com/pomp/hskai/core/design/Spacing.kt` (Android) in `HSK-AI-Bot`. This is **logical design-scale parity**, not a claim that CSS px and Android dp map to identical physical pixels on every device. Use the established tokens; if a new relative-unit strategy is proposed, first verify its behavior against current layouts rather than silently redefining the root font size.

## Usage guidelines

### Always use a token — never a raw value

Use HSK AI's approved 4-unit spacing scale to realize the **professional rhythm, grouping and spatial hierarchy**; the current layout's exact padding/gaps are not fixed targets. Avoid arbitrary per-screen values (such as 13px, 17px or 22px) without a deliberate documented optical exception. PWA must reference the approved CSS variables and Android must use `PompSpacing` values. During the cross-platform UI audit, identify historical hard-coded values and assess each before migration; do not change production layouts blindly or assume that any non-token measurement is automatically a spacing defect.

### The same relationship gets the same space

If the gap between a section heading and its content uses the 16-step (`--hsk-space-4` / `PompSpacing.Large`) in one comparable screen, use that same step in other comparable screens. A different learning task may need a different relationship; consistency means matching purpose, not forcing identical spacing everywhere.

### Spacing is not a substitute for structure

Adding more space to make something feel "important" or "separated" is a workaround, not a solution. If an element genuinely needs visual distinction, that should come from hierarchy, weight, or color — not just extra margin. Space supports structure; it doesn't create it.

### Spacing can't fix content overload

If a layout feels crowded and adding more space doesn't help, the problem is likely the number of elements competing for attention — not the gaps between them. More space around too many things just makes a bigger crowded layout. When spacing isn't solving the problem, the right conversation is about content prioritization, not spacing values.

### Component spacing is already handled

Spacing within professional shared UI components (for example, button padding) belongs to their component specification and should not be overridden ad hoc. Existing component spacing that contradicts the professional target is a future shared-component redesign candidate, not a global exemption. Layout authors control spacing between components and inside new composed groupings. Keep canonical Panda/approved-character proportions, established lesson feedback effects and AI Voice Orb geometry intact; do not resize or reposition them mechanically just to fit a spacing step. Correct an actual accessibility or layout defect through the relevant component design, not arbitrary overrides.

### Negative space is a design decision

A large region of intentional emptiness can do real work — focus attention, signal importance, give a moment room to land. When an element needs to register on its own (a primary call to action, an empty state, a critical alert), the space around it is part of the design, not leftover room. This is different from the rhythmic spacing between content elements and shouldn't be confused with adding unnecessary padding.

## Types of spacing

There are several types of spacing we can use to place elements within layouts and components. Although you're most likely going to use them all when designing your products, it's important to know what types of spacing are commonly used.

### Padding

Padding is the distance between the outside edge of an element and the content inside of it.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Padding illustration. Source asset: `./assets/spacing/types-of-spacing-1.png`.

### Gap

Gap is the space between elements inside a container. Unlike padding, it doesn't affect the distance to the container's edge, it only controls how far apart the elements inside are from each other.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Gap illustration. Source asset: `./assets/spacing/types-of-spacing-2.png`.

### Margins

Margins are the space around the outside edge of a component.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Margins illustration. Source asset: `./assets/spacing/types-of-spacing-3.png`.

## Spacing examples

Here are some examples of use which might help guide your decisions when applying spacing within your designs. These are just suggestions, not strict rules you must follow. If you are unsure about what spacing works best between the components of your design you can use the following examples as a reference point.

### Layout spacing

Make sure to use vertical spacing as a way to create meaningful blocks of content, using bigger and smaller spaces to improve the visual hierarchy of your layout and to keep a consistent vertical rhythm within the page.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Layout spacing example. Source asset: `./assets/spacing/spacing-examples-1.png`.

### Grouped content

When you're composing a custom grouping — a card, a module, a section of related content — use padding and gap consistently to create a clear visual hierarchy. Smaller values bring related elements closer together; larger values signal separation between distinct content areas. This is different from spacing inside a pre-built system component (a Button, an Input) — that's fixed by the component and isn't yours to adjust; see Component spacing is already handled above.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** Component spacing example. Source asset: `./assets/spacing/spacing-examples-2.png`.

### Typography spacing

Prioritize readability of Chinese Hanzi, pinyin and translations. Keep related text close enough to be recognized as one learning unit without collisions or cramped line spacing; use larger gaps to separate distinct questions, answer options and feedback. Spacing tokens control margins and padding; readable line-height and text scaling are governed by typography and must not be forced to 4-point increments.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** Typography spacing example. Source asset: `./assets/spacing/spacing-examples-3.png`.

## Accessibility

### Spacing scales with user preferences

The current PWA spacing tokens are CSS px values, which scale under page zoom but do not automatically respond like rem values to every text-only preference. Android spacing uses dp, while font scaling operates separately. Test PWA zoom and text scaling, as well as Android display/font scaling and small screens; check at 150% and 200% and assess up to 400% zoom where supported. Learning content, especially Hanzi/pinyin/translation and interactive feedback, must not overlap, clip, or require unnecessary horizontal scrolling. Do not alter the root rem conversion to mimic Khan Academy without testing.

### Touch targets require minimum spacing

Interactive controls must have touch target areas of at least **44×44 CSS px on iPhone PWA** and **48×48 dp on Android**. The visible icon may be smaller than its hit area. Keep sufficient separation to avoid accidental taps, including for lesson answer choices and back/close controls. Validate existing components during the cross-platform UI audit; do not assume all current screens already comply.

### Whitespace aids readability for cognitive accessibility

Adequate spacing between text elements and content groups benefits users with cognitive disabilities, attention difficulties, and reading disorders. Dense layouts are not inherently inaccessible, but spacing decisions in reading-heavy contexts should account for the full range of users.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: scale.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/spacing/scale.png)

- [scale.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/spacing/scale.png) — exact source blob `199b41022cec` (illustrated above)
- [spacing-examples-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/spacing/spacing-examples-1.png) — exact source blob `417ea08481c5`
- [spacing-examples-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/spacing/spacing-examples-2.png) — exact source blob `19fa35d312d9`
- [spacing-examples-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/spacing/spacing-examples-3.png) — exact source blob `ec8bbb6de53a`
- [spacing.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/spacing/spacing.png) — exact source blob `c2d862abb09f`
- [types-of-spacing-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/spacing/types-of-spacing-1.png) — exact source blob `5dd5ba157b04`
- [types-of-spacing-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/spacing/types-of-spacing-2.png) — exact source blob `ac414f766f31`
- [types-of-spacing-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/spacing/types-of-spacing-3.png) — exact source blob `093968a41488`
