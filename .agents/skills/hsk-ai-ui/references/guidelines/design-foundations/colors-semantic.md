> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/colors-semantic.mdx`, Git blob `147d3f2d1cee957c8ec1ba46155e03ef9f97d1c2`; 1 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# HSK AI semantic color tokens

HSK AI color names must describe **actual product roles and states**, not an external design system's organizational structure. The authoritative current sources are `app/static/course_v3_data/design-tokens.css` for the PWA and `android/app/src/main/java/com/pomp/hskai/core/design/Color.kt` for Android in the HSK AI app repository. The table below inventories **existing values**, not a claim that every component already uses them consistently.

## Color roles

| Purpose | Existing PWA token(s) | Intended use |
| --- | --- | --- |
| Main background | `--hsk-paper` | Main learner screen / app canvas |
| Raised content | `--hsk-paper-raised`, `--hsk-card-surface` | Cards, menus and raised surfaces |
| Primary text | `--hsk-ink` | Essential learning content, controls and headings |
| Supporting text | `--hsk-ink-secondary` | Noncritical explanations and labels |
| Disabled text | `--hsk-ink-disabled` | Controls that cannot currently be used; not an error state |
| Dividers | `--hsk-divider` | Separating surfaces without unnecessary emphasis |
| Primary accent | `--hsk-cinnabar`, `--hsk-cinnabar-dark`, `--hsk-cinnabar-ink`, `--hsk-cinnabar-soft`, `--hsk-on-cinnabar` | **Non-destructive brand and primary-action contexts** |
| Learning success | `--hsk-jade`, `--hsk-jade-ink`, `--hsk-jade-soft`, `--hsk-on-jade` | Confirmed positive learning/action state where implemented |
| Reward/milestone emphasis | `--hsk-gold`, `--hsk-gold-ink`, `--hsk-gold-soft`, `--hsk-on-gold` | Real milestone or recognized Pro presentation, not a made-up economy |
| Accent/attention | `--hsk-flame`, `--hsk-flame-ink`, `--hsk-flame-soft`, `--hsk-on-flame` | Established visual emphasis when needed |
| Informational accents | `--hsk-blue`, `--hsk-blue-soft` | Existing informational surfaces |

The PWA does **not** define an independent `--hsk-critical` or `--hsk-warning` token in this file. Do not fabricate those names or treat the brand accent as a universal destructive/error token. When an error or warning needs a semantic color, inspect the actual component or Android color scheme and propose a verified token addition as a **future change**, not a current property.

## Actual theme values

These are **documented current PWA values** for the most important roles, not an arbitrary new palette:

| Existing token | Light | Dark |
| --- | --- | --- |
| `--hsk-paper` | `#FDF9F0` | `#002F49` |
| `--hsk-paper-raised` | `#FFFFFF` | `#073B55` |
| `--hsk-ink` | `#211D17` | `#F5FAFD` |
| `--hsk-ink-secondary` | `#665D50` | `#B8CDDA` |
| `--hsk-divider` | `#EAE0CC` | `#17617D` |
| `--hsk-cinnabar` | `#E04A40` | `#20BCEB` |
| `--hsk-jade` | `#2FA06A` | `#48D99A` |
| `--hsk-gold` | `#E9A916` | `#F4C95D` |
| `--hsk-flame` | `#FF9600` | `#FF6B66` |

**Important:** `--hsk-cinnabar` is the existing brand-action role name even though its **dark-mode appearance becomes cyan**. Do not hardcode red in both themes, infer that cyan means error, or bind success and incorrect-answer semantics to a decorative brand color.

## Semantic-system design method (source reference)

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Historical semantic token hierarchy diagram; source category names and palette are illustrative, not HSK AI token contracts. Source asset: `./assets/colors/semantic-tokens-hero.png`.

The professional insight is to **separate raw color values from interface purpose**. A semantic role can be defined by state (ordinary, selected, success, warning, error or disabled), foreground/background context and theme. The source's former domain/layer/intensity taxonomy is **not a HSK AI token API**. HSK AI's actual tokens above and native Material roles govern implementation.

For each role, specify the component, text/background pairing, light/dark values, contrast outcome and a non-color cue. When a needed role is absent, record it as a **design gap**, not an already implemented CSS property. Verify that a visually similar brand accent does not silently substitute for a destructive state.

## Application rules

1. **Role before hue.** Confirm whether the meaning is action, ordinary reading, learning result, error, warning, Pro/milestone, or decorative emphasis.
2. **Product-proven state.** Successful lesson completion, saved settings, payment/Pro and results only use their status visuals after the authoritative state confirms them. Color cannot imply an unverified result.
3. **Answer feedback.** Correct and incorrect lesson feedback must include text/shape/icon and the approved Panda or lesson-character reaction where available. Do not rely on red/green alone, and do not turn incorrect-answer feedback into a destructive-action dialog.
4. **Accessible contrast.** Normal text should meet WCAG's usual minimum 4.5:1 and large text and required graphical controls at least 3:1 against their real surrounding surfaces. Confirm **actual foreground/background pairings**, including disabled states and both themes; this page is not proof that every current token pairing already passes.
5. **No source-theme inheritance.** This is not a four-domain Wonder Blocks system. HSK AI has no mandatory Gems, school-math, source-identity colors, or source-only role/score tokens.
6. **Cross-platform parity.** Align semantic intent between the current PWA CSS roles and Android `PompColors` / `PompPalette`, but do not falsely claim literal variable-name or pixel equality. Verify screenshot contrasts and legibility.
7. **Characters and Orb.** Respect the existing Panda and side characters' canonical artwork. AI Voice's red pearlescent Orb is its own approved interactive visual and does not have to follow a flat spot-illustration palette.
8. **Expandable text.** A collapsed optional explanation has at most two visible lines and a top-right ⌄/⌃ icon; never use an accent color as the **only** indication it can be opened.
9. **No unauthorized new color tokens.** If design work calls for a new warning/error/focus role, define its actual intended semantics, test light/dark accessibility and implement it in the real platform in a separately approved change.

## Restored semantic-token architecture — HSK AI adaptation

### Naming anatomy

- Name a proposed design token by **role, visual layer, interaction state and emphasis** rather than a raw hue: for example, an ordinary primary action foreground, an error border or an elevated card background. The vocabulary is a **design method**, not a claim that an identically named CSS variable exists today.
- A token's **layer** matters: background, foreground, border, shadow, overlay and illustration colors have different contrast and compositing requirements. A shadow value must not be substituted for a warning or icon foreground color.
- A token's **context** expresses meaning. Base is the app canvas; primary/non-destructive is an action, Neutral carries no extra verdict, Disabled prevents interaction, Success confirms a verified result, Warning requests attention, Critical denotes actual failure or dangerous action, and Overlay separates a blocking foreground surface from the underlying content.
- Intensity is relative to the surrounding surface, not a universal lightness number. Define resting, elevated, hover/pressed, focus, selected and disabled behavior only where those states are real and implementable on the platform.

### Controlled specialization

- Prefer existing **PWA CSS and Android native color roles** for every ordinary UI element; propose new aliases only when a repeated **HSK AI** semantic purpose cannot be expressed safely with them. Changes to either platform require separate code and contrast tests.
- HSK AI learning colors may distinguish verified progress, HSK study levels or feedback states **only when the feature and measurement exist**. Do not import source-school Math, Gems, school-role, overdue-assignment or character-only color domains.
- Separate **internal component-state tokens** from publicly recommended component-facing tokens. A future internal button-pressed color is a component implementation detail, not permission for arbitrary screens to use its raw hex.
- Graphics/character colors are separate from functional UI status colors. Canonical Panda, Longlong, Hehe, Wuwu, Yueyue and the pearlescent red Orb retain their original artwork and motion; do not force their red into the Critical palette.

### Review before adopting a token

1. Identify the user action/state, actual source and accessible non-color cue.
2. Check light **and** dark backgrounds, content contrast and focus visibility for each state.
3. Check the existing CSS/native code: is this token implemented or merely a target proposal?
4. Verify status meaning is consistent across lesson, account, subscription, onboarding and reports.
5. Record whether the token replaces redundant values; do not create a fifth visually similar “red” role without an approved need.

## Implementation boundary

These rules document HSK AI meaning and existing tokens. They do not migrate app fonts, CSS, Kotlin palettes, scoring, reward semantics or account flags. Documentation renderers may still use external helper components for drawing examples; those helpers are not app-level requirements.
