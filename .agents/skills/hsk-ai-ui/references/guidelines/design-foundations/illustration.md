> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/illustration.mdx`, Git blob `e9947b3c1fa26573c28ed97b716878dd04e0dd5f`; 3 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# HSK AI illustration

Illustration supports Chinese-language learning, explains important states and establishes the visual identity of HSK AI. **Only canonical HSK AI characters and approved assets** may be presented as product artwork. A design source or unrelated mascot is not a valid HSK AI asset.

## Principles

### Identity and consistency

Keep the established **Panda (熊猫)** recognizable across PWA and Android, including its face, eyes, ears, proportions, silhouette, palette and approved expressions. Use the app's actual art/rendering code rather than a stock panda or an approximate generated substitute.

The current HSK AI character pack also includes **Dragon/Longlong (龙龙), Crane/Hehe (鹤鹤), Monkey/Wuwu (悟悟) and Rabbit/Yueyue (月月)**. These are different approved learning roles, not arbitrary alternate brand logos. See [HSK AI characters](../design-components/hsk-ai-characters.md) and verify current mobile usage before adding art to a screen.

### Meaning before decoration

Every image must serve orientation, learning instruction, a real feedback state or a meaningful celebration. An illustration should not compete with the exercise, Hanzi/pinyin/translation, answer choices or the next action.

Do not add decorative mascots to every input, utility screen, payment state or report. Calm and information-dense contexts generally need fewer images than a lesson or verified celebration.

### Contrast and accessibility

- For meaningful non-text graphics and control boundaries, verify actual required contrast (normally **3:1** for applicable WCAG AA graphical objects); contrast standards are not a guarantee that a particular current palette passes.
- Decorative confetti or accent shapes have no independent information contrast requirement, but must not obscure reading.
- A correct or incorrect response needs a legible non-color signal, not merely a green/red face. Describe meaningful character states to accessibility tools; do not repeat redundant decorative illustrations.

### Character and AI Voice exceptions

Ordinary supporting illustrations may be restrained, simple and mostly flat. **Do not flatten or recolor the approved character artwork** to enforce an arbitrary generic style.

The AI Voice Orb is a **separate red, pearlescent, softly glowing three-dimensional interactive visual**. Preserve approved Listening, Thinking and Speaking states, keyboard overlay behavior and reduced-motion alternatives. It is not a generic flat icon or interchangeable cartoon.

## When to use illustration

| Situation | HSK AI treatment |
| --- | --- |
| Onboarding | A real approved Panda pose may guide the learner when it adds clarity; never hide a required choice or keyboard. |
| Correct answer | Preserve the actual lesson character's positive response once the answer state is established. |
| Incorrect answer | Preserve the actual supportive wrong-answer reaction and readable correction, never shame the learner. |
| Learning milestone | Celebrate only a genuinely confirmed milestone or recorded completion; keep motion proportional. |
| Error/empty state | Prefer explicit text/retry and a small approved supporting spot illustration if it communicates the situation. |
| AI Voice | Use the distinct approved Voice Orb and its actual states. |
| Settings, reports, payments | Prioritize accurate status, accessibility and actions; illustration is optional, not required. |

## Supporting art types

**Spot illustration:** small asset clarifying an available state, empty view or feature explanation. Always include text that communicates the needed action or meaning.

**Scene:** a larger learning environment only when it directly supports the content and uses consistent approved characters. Do not introduce an unrelated cartoon as part of a generic background.

**Accent:** decorative confetti, stars or minor shapes only where they do not distract from Hanzi, pinyin, important controls or verified status.

## Original professional illustration-type examples

These original reference images illustrate **three forms of supporting artwork**. They are **not HSK AI brand assets, approved mascot styles, or production illustrations**. The actual Panda and other canonical characters always supersede their look.

### Spot illustration — one focused idea

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Original design-system example of a small spot illustration; source shapes and colors are not HSK AI artwork. Source asset: `./assets/illustration/types-of-illustration-3.png`.

A spot image should explain one meaningful state without occupying most of the page. For HSK AI an eligible example would be a **currently supported** empty state or small learning help area. Pair the graphic with the real message and action; do not insert a random character merely to decorate an alert.

### Scene — purposeful context

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Original scene composition reference; not a canonical HSK AI character scene. Source asset: `./assets/illustration/types-of-illustration-4.png`.

A scene should have a focal subject, a restrained background and a clear relationship to the user's current task. Keep enough breathing room for Hanzi, tone-marked pinyin, answer choices and narrow phone layouts. Do not trace source characters or shift approved Panda anatomy.

### Accent — strictly decorative

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Original decorative accent reference illustrating small shapes and celebration effects. Source asset: `./assets/illustration/types-of-illustration-5.png`.

Accent shapes such as confetti may support a verified celebration but must carry **no required information**. Their color and animation may be reduced or removed without losing meaning. Never use an accent as evidence that a lesson or payment succeeded.

## Motion, scale and responsive layout

- Keep mobile safe areas and keyboard clear; an illustrated panel must adapt to the actual phone width rather than a desktop-specific fraction.
- Use the current renderer for character scale/mood and honor reduced-motion preference. Meaning must not disappear when motion is off.
- Preserve approved feedback for **both correct and incorrect** lesson answers. Avoid unrequested permanent animations that interfere with pronunciation practice or AI Voice.
- Do not use one universal icon/character size on every platform; validate PWA and native Android renders at actual screen dimensions.
- Avoid clipping the Panda, tone marks or the red Orb under bottom navigation or a floating popup.

## Production asset approval

1. Locate the actual approved art in the current HSK AI application or confirmed owned assets.
2. Compare screen, pose, expression and proportions against the existing implementation.
3. Check the intended lesson/user state and ensure an animation or illustration will not leak a hidden answer or claim unverified rewards.
4. Inspect light/dark colors, accessible text alternative, touch layout and reduced-motion behavior.
5. If the canonical source is unavailable, report the missing asset. **Do not improvise a replacement brand character.**

## Restored illustration audience and type rules

### Calibrate to context, not to an external product

- Learner-facing explanations and **verified** learning celebrations can be approachable and expressive while keeping the task, Hanzi, pinyin, translation and answer feedback visible.
- Reports, settings, payments and account-recovery screens need a restrained emotional register: concise text and controls first. An illustration is optional; its absence is preferable to unrelated decoration or a misleading “success” Panda.
- Only the HSK AI product's real canonical **Panda, Longlong, Hehe, Wuwu and Yueyue** artwork is valid for character-bearing UI. Keep the relevant character's face, silhouette, proportions, style and recognition consistent across platforms. Correct **and** incorrect reactions are preserved.
- The **red pearlescent AI Voice Orb** is an independent interactive rendering with its own Listening, Thinking and Speaking state behavior, not a generic flat geometric accent or a different company's assistant character.

### Three functional illustration tiers

- **Spot:** one focused concept, suitable for an optional state explanation. Use simple forms and keep it near the associated instruction; never invent an app-specific feature to justify a spot.
- **Scene:** a composed environment for genuine storytelling or onboarding context. Reduce detail at phone widths; it cannot replace meaningful written steps or accurate iPhone Safari guidance.
- **Accent:** purely decorative shape or confetti with no semantic payload. Hide it from assistive technology, suppress unnecessary animation under reduced-motion preferences and keep it away from inputs.
- Ordinary *new* supporting illustrations can be simple, flat and geometric with approved theme roles; **do not flatten, recolor or restyle** canonical characters or the Voice Orb to match them.

### Contrast, alt text and reuse rights

- If removing an image would remove essential meaning, supply a text alternative and ensure the important graphical features meet applicable contrast; if purely decorative, use an empty/decorative text alternative.
- The source's old character and product artwork may teach layout but **does not grant rights or identity** to reuse. For public release, use original HSK AI-owned assets or individually cleared generic diagrams; an older Git commit is not a license.
- Validate readability, overlap, alt text, phone crops, responsive motion and light/dark appearances before approving an illustration for production.

## Source of truth and scope

PWA: `app/static/assets/characters/hsk-character-pack.js`, `hsk-character-motion.js` and related HSK AI screens. Android: `core/design/components/HskCharacters.kt`, `feature/lesson/LessonCharacters.kt`, and the current Voice renderer. These paths are references into the **read-only production repository**, not files in this design project.

This is HSK AI-only documentation. It contains no imported art, requirements, score rules or character policy from other products; making changes to production character rendering is a separate task.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: types-of-illustration-5.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/illustration/types-of-illustration-5.png)

- [types-of-illustration-5.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/illustration/types-of-illustration-5.png) — exact source blob `1363aa201082` (illustrated above)
