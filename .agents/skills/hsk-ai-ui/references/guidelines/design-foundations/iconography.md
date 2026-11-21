> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/iconography.mdx`, Git blob `deafe2f3ef3b6f61afbdca9f605d349f9b6dead8`; 5 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# HSK AI iconography

Icons should support clear, familiar, accessible interaction in the HSK AI learner app and authorized admin tools. They do **not** determine the brand or replace actual Panda, learning characters, the Pro crown or the red AI Voice Orb.

## Principles

### Consistent visual vocabulary

- Reuse each platform's **current approved icons and components** where they already serve a function. Do not migrate the PWA or Android icon system to another library without a dedicated audited project.
- For **new generic actions** without an existing canonical asset, a consistent, approved icon family such as Phosphor may be used with a proper accessible label. Preserve canonical character, Voice Orb and official brand icons. **For ordinary generic interface glyphs, a consistent professional Phosphor family is the intended design target**; later PWA/Android redesign may update inconsistent existing generic icons after semantic and affordance review, not as a blind automated bulk replacement.
- Do not mix arbitrary downloaded vector artwork, unrelated product mascots or visually mismatched stroke/corner styles in the same component.
- Prefer a restrained number of icon sizes and weights for the actual mobile screen rather than copying a fixed pixel scale from a different product.

### Meaning and context

- Common actions such as close, back, search and information may show an icon alone **only** when their meaning is obvious in context and they still have an accessible name.
- Less familiar learning actions require a visible clear label or an established local convention. Pinyin replay, reveal translation, review mistake and lesson actions must never be ambiguous.
- Avoid using an icon when concise readable text communicates the action more clearly.
- Preserve the **actual HSK AI** primary navigation meanings and selected/disabled/error states; a fill, stroke or accessible state can help convey selection, but color alone is not enough.

## Scale and touch targets

| Context | Design principle |
| --- | --- |
| Inline explanatory icon | Keep it visually subordinate and aligned with readable text. |
| Small status icon | Pair with a meaningful word/state and sufficient contrast. |
| Action icon | The glyph can be small but its invisible touch target must remain comfortable. |
| Navigation icon | Use the same approved visual dimensions/stroke across related tabs and platforms. |
| Larger illustration | Treat as graphics/characters, not as an enlarged generic interface icon. |

Minimum interactive targets: **44 × 44 CSS px** on iPhone PWA and **48 × 48 dp** on native Android, where relevant. This does not mean every *visible glyph* must be 44–48 units wide.

## Professional icon references and HSK AI decisions

The five illustrations below are **historical source design examples**. They demonstrate professional icon geometry, hierarchy, labeling and state, **not** the product's existing app icons or a requirement to migrate every PWA/Android icon.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Historical iconography overview illustrating consistency of stroke and recognizable symbols; not an HSK AI icon inventory. Source asset: `./assets/iconography/iconography.png`.

### Library consistency and migration policy

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Reference icon-library overview; existing HSK AI icons retain their current approved assets until an audited migration. Source asset: `./assets/iconography/icon-library.png`.

For **new ordinary generic icons**, use the previously approved Phosphor family with a consistent stroke vocabulary, and adopt a smaller number of size/weight roles. Existing production icons are **not** replaced in this guideline-only phase, but inconsistent generic icons should be identified as future UI/UX migration candidates. Keep the original professional requirements for stroke, weight, optical alignment, roles and state consistency; only actual HSK AI branded assets are protected exceptions.

| Reference glyph size | Source visual weight | Professional use; verify per app component |
| --- | --- | --- |
| 12px | Bold | Compact indicators, never a 12px-only tap target |
| 16px | Bold | Inline indicators, badges, inputs |
| 20px | Bold | Common button/status glyphs |
| 24px | Regular | Navigation or icon buttons |
| 48px | Regular | Large illustrative utility symbol, not a mascot |

These source values are **illustrative**; existing HSK icon dimensions and the iPhone 44 CSS px / Android 48 dp interaction targets take priority. Do not enlarge a glyph only to satisfy tap-area sizing.

### Selection, labeling and weights

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Reference example of sourcing icons consistently; a source Figma library is not HSK AI's production icon repository. Source asset: `./assets/iconography/usage-guidelines-1.png`.

Use one coherent approved generic visual family for a new feature, rather than assembling arbitrary SVGs from unrelated libraries. Source icons such as teacher, classroom, Gems, Khanmigo or assessment roles **must not be ported**.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Reference comparing familiar standalone close/back icons with less obvious symbols that need labels. Source asset: `./assets/iconography/usage-guidelines-2.png`.

- Close, back or search can be icon-only in a known position **with an accessible name**.
- New study actions, reveal translation, replay pronunciation and review mistakes need a visible label or a well established product-specific convention.
- A tooltip by itself is not a sufficient touch interface label when a symbol is unfamiliar.
- Do not communicate selection with a color change alone.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Reference comparison of icon visual weights and selected states; not an instruction to recolor HSK characters. Source asset: `./assets/iconography/usage-guidelines-3.png`.

Regular/Bold/Fill offer a useful visual hierarchy for newly approved generic icons; reserve Fill for actual selected states when a clear state cue is needed. Avoid hard-coded source library rules for every platform icon, and review readability, contrast and Unicode fallback on physical devices. Custom Panda, correct/incorrect reaction, Pro crown and Voice Orb artwork **remain outside** the generic icon family.

## Correct and incorrect lesson feedback

Keep the established Panda or routed lesson character reaction **for both outcomes**, plus a meaningful success/error cue and localized explanation when necessary. An icon alone must not override the learning state or falsely signal an unverified completion.

The error state of a text field, a wrong exercise answer and a destructive account operation may all use different language and colors; they are not interchangeable just because an X icon appears.

## Two-line optional text disclosure

When a truly **optional supporting explanation** exceeds two rendered lines, it may be clamped to **at most TWO fully visible lines** and expanded **in place** using only a top-right **⌄/⌃** icon. The visual control has **no visible text label**, but must provide an accessible localized name, button semantics, a clear state and a large enough tap target.

The icon remains visible in the upper-right corner when expanded. Determine whether it is needed by measuring **the fully rendered text against the collapsed two-line layout**, not by testing the expanded text height. Never collapse a required question, answer, error, payment term or essential lesson text.

## Accessibility

- For meaningful action icons, give screen-reader users an accessible name and focus. Hide redundant decorative icons.
- Verify non-text interface contrast (normally **3:1** for applicable meaningful indicators), including dark mode and disabled states.
- Make selected/expanded/error states understandable through more than a color change.
- For in-app Chinese labels, preserve Hanzi, tone-marked pinyin and the learner's localized language.
- Respect platform navigation expectations, keyboard/safe-area clearance, text scaling and reduced-motion settings.
- Do not replace source-approved artwork with random cartoon symbols merely because a generic icon library cannot render it.

## Restored icon scale, weights and governance

### Proposed generic icon sizing rules

- Use **Phosphor** for new ordinary interface icons, with a clear mapping of glyph meaning across PWA and Android. **Regular, Bold and Fill** are the preferred available weights for proposed new UI; Thin and Light are fragile at small sizes, and Duotone should not be introduced casually.
- The source sizing method is useful as a **starting guideline**, not a verified implementation fact: roughly **16px Bold** for inline status, inputs and badges; **24px Regular** for icon buttons and ordinary navigation; **48px Regular** for a large file/action symbol. Final visual size, optical weight and dp/px scaling must be validated on both platforms.
- Reserve **Fill** for selected/active emphasis where it has a distinct accessible meaning. Do not arbitrarily change a glyph's weight across states, and do not turn a destructive action into a decorative bold icon.
- Low-emphasis affordances (such as a drag handle) may need a less prominent weight; high-emphasis confirmation may need a stronger one. These are deliberate exceptions requiring a visual review, not free styling choices.

### Labels, touch and prohibited substitutions

- Common close, back and search glyphs may be icon-only when a user understands the context **and** an accessible button name exists. For unfamiliar actions, use an adjacent visible label or an appropriate persistent explanation, not a hover-only hint.
- Match actual HSK AI button tap areas; the icon's drawn size is **not** its full interactive target. Evaluate PWA at least 44 CSS px and Android's native 48 dp expectation where applicable, without enlarging glyph artwork unnecessarily.
- An action icon's visual foreground and focus state must meet the required contrast in both themes; disabled presentation needs semantic disabled state, not a blanket untested opacity.
- Explicit **right-or-wrong** feedback remains a combination of the existing character expressions/effects and accurate educational explanation. A check or X may supplement, never replace, these reactions.
- The two-line optional-disclosure chevron is **⌄/⌃ at top-right, icon only visually**, with screen-reader button name, expanded state, sufficient target and no lost required text. Never put an illustrated character or custom lesson mark into Phosphor merely for visual uniformity.

### Approval and source boundaries

- No upstream Gems/teacher/class/assistant glyph becomes HSK AI product policy. Existing canonical characters and AI Voice Orb are exceptions because they already have approved HSK AI identity.
- Record the chosen glyph, weight, size, touch area, theme pairing, accessible name and real platform availability before declaring a new icon mapping final.

## Implementation boundary

These are HSK AI design rules. No production app icon dependency, UI screen, Native Compose icon set or Panda/Voice renderer is changed in this documentation-only revision.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: icon-library.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/iconography/icon-library.png)

- [icon-library.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/iconography/icon-library.png) — exact source blob `ae5d4f81e22e` (illustrated above)
- [iconography.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/iconography/iconography.png) — exact source blob `b3dc7449db36`
- [usage-guidelines-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/iconography/usage-guidelines-2.png) — exact source blob `80490285d598`
- [usage-guidelines-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/iconography/usage-guidelines-3.png) — exact source blob `891d3f05e011`
