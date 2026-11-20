> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/typography.mdx`, Git blob `176f0142305063ddfd3a3d59b4cb70cda1696b33`; 0 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# Typography

HSK AI teaches Chinese through **Hanzi, pinyin and a learner-language meaning**. Typography is therefore part of instructional accuracy, not only visual styling. This HSK AI-specific foundation is **new**: the upstream Khan Academy guidelines do not contain a standalone typography page to preserve. The original [Text field](../design-components/text-field.md) and component-copy guidance remain authoritative for their own interaction patterns.

> **Documentation boundary:** The current PWA and Android typography below is an **implementation inventory, not an endorsement that every current font size or face is optimal**. This page defines a professional target hierarchy to validate visually and accessibly before any code migration. Preserve real HSK AI learning content, characters, lesson states, theme semantics and approved interactions. This file does not install fonts, change code or reveal an exercise answer.

## Principles

1. **Accurate first.** Hanzi, pinyin tone marks, character order and translation meaning must remain correct after layout, scaling and line wrapping.
2. **The exercise determines what is visible.** A teaching card may display Hanzi, pinyin and translation together; a listening, recognition or quiz task may deliberately hide one or more until the relevant reveal state.
3. **One reading hierarchy.** In an ordinary new-word display, the existing PWA order is **Hanzi → pinyin → meaning → audio/replay**. When a task is specifically about pronunciation or translation, adapt emphasis to that task without mixing the text's meanings.
4. **Use a professional, coherent type system.** Reuse the product's existing semantic font roles where suitable, but audit and improve inconsistent sizes, weights and fallbacks before rollout. Generic source-design fonts or demo swatches must not override HSK AI themes.
5. **Localization is content, not decoration.** Uzbek, Russian and Tajik labels and translations need real space and meaningful accessible labels. Never shrink a word until a tone mark becomes unreadable.

## Existing typography sources

The production PWA already defines these values in `app/static/course_v3_data/design-tokens.css`:

| Existing token | Current value or role | HSK AI use |
| --- | --- | --- |
| `--hsk-font-ui` | `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Arial, sans-serif` | Menus, labels, Russian/Uzbek/Tajik translations, buttons and pinyin with suitable glyph fallback. |
| `--hsk-font-cjk` | `"Songti SC", "STSong", "Noto Serif SC", "Noto Sans SC", serif` | Prominent Hanzi on appropriate PWA lesson surfaces. |
| `--hsk-section-title-size` | `20px` | An existing section title reference, **not** a global size for words or pinyin. |
| `--hsk-section-title-line-height` | `1.2` | Existing section-title proportion; not a universal text line-height. |
| `--hsk-ink` / `--hsk-ink-secondary` | Theme-dependent text colors | Primary learning text and supporting explanations. |

The light theme currently uses dark ink on light paper and the `--hsk-cinnabar` accent `#E04A40`. The dark theme uses light ink on dark paper and **the same token** changes to cyan `#20BCEB`. **Do not hard-code the light accent in dark mode.**

On Android, `android/app/src/main/java/com/pomp/hskai/core/design/Type.kt` already defines `PompTypography` (32/24/20/16/14 sp role sizes) plus `PompTextStyles` (`hanziLarge` 56 sp, `hanziMedium` 32 sp, `pinyin` 16 sp). Android currently uses the platform's default sans font for ordinary UI and a generic Serif family for learning Hanzi. These are **observed values, not evidence that all other Android screens use the role styles consistently**. A PWA `px` value is not a 1:1 Android `sp` instruction. No new font file or web font dependency is introduced by this documentation.

## Professional typography direction

The original HSK AI PWA already uses a sensible system UI stack, while Android has a real Material 3 typography definition. This is a good foundation, **but the screens are not yet one consistent professional text system**: the PWA mixes numerous ad-hoc sizes (including some secondary labels around 9–11 px); different screen components vary in weight, spacing and line height. A polished outcome requires clear roles and visual verification, not merely replacing the font family.

### Font families and visual character

- **Interface and localized body:** retain a native system sans-serif approach — Apple system text / San Francisco on iPhone, Android's Material 3 system sans typography on Android — with appropriate Cyrillic, Latin and tone-mark glyph fallback. Standardize actual text roles across screens rather than bundling a fashionable but unverified third-party font.
- **Chinese body text and smaller Hanzi:** prefer readable modern Chinese sans-serif glyphs, such as available PingFang SC or Noto Sans SC system fallback, when stroke clarity is better. Do not force a thin decorative serif for small Chinese sentences.
- **Prominent learning Hanzi:** retain the approved Songti/Chinese serif appearance on screens where it is legible and visually intentional; compare it directly against a modern CJK sans option on small devices. Do not enforce one global serif swap without checking the correct/incorrect states, lesson cards and character recognition.
- **Pinyin:** use the readable UI sans stack with reliable macrons/caron/umlaut glyphs and enough vertical headroom. Prefer restrained weight and near-normal tracking; heavy bold and exaggerated letter-spacing make tones harder to scan.
- **No gratuitous font inventory:** one coherent UI family with its script fallbacks, plus one deliberate Hanzi display role, is the target. Do not add font downloads or font licensing dependencies without a specific reason and an accessibility/performance review.

### Proposed semantic type scale (design target, not existing app configuration)

| Text role | PWA reference range | Android reference | Intended hierarchy |
| --- | --- | --- | --- |
| Large, focused Hanzi | About 40–56 CSS px where a word is the main content | Existing 32/56 sp Hanzi roles as starting points | Most prominent only in learning-focused contexts |
| Chinese example/sentence | About 22–28 CSS px when it is the main exercise text | Native scalable style chosen by screen | Readable strokes, no clipped lines |
| Page/section heading | 20–24 CSS px | Existing 20–24 sp title roles | Clear title, restrained use of heavy bold |
| Main body and translations | Normally 16 CSS px | Existing 16 sp body role | Comfortable continuous reading, sufficient line-height |
| Pinyin | Usually 16–20 CSS px; can be larger on dedicated pronunciation screens | Existing 16 sp pinyin role; scale where needed | Tone marks always readable and visually associated with Hanzi |
| Secondary hints and metadata | Usually 14 CSS px; 12–13 only for genuinely nonessential short metadata | Existing 14 sp body/label roles where suitable | Supportive, not the primary instruction |
| Critical instruction, price, limit, validation/error | **Never** reduced merely to make a compact card | Scalable body/label style suited to importance | Full content visible and understandable |

These ranges are **starting points for visual prototypes and audits**, not a requirement to update every CSS declaration blindly. Follow actual mobile accessibility scaling, language length and existing HSK AI component constraints. Aim for a small number of consistently named roles, typically regular (400), medium (500), semibold (600) and bold (700) where the selected platform font supports them; do not mix arbitrary weights 550/650/750/850 across otherwise equivalent screens.

- General body line-height should allow easy reading (roughly 1.45–1.6 on PWA where appropriate). Hanzi and pinyin require enough line-height to preserve strokes and diacritics; do not force an aggressively tight fixed-height text box.
- Avoid heavy all-caps, unjustified tracking and font-weight mismatches, especially on localized text and tonal pinyin.
- Use the approved light/dark semantic color roles, readable contrast, coherent spacing and natural wrapping. Do not attempt to compensate for poor hierarchy by creating more colored text, badges or decorations.
- A design reviewer must compare **actual screenshots** for PWA Safari and Android at ordinary and enlarged text, including Hanzi, tone marks and all three learner-interface languages, before approving a typography migration.

## Inline collapse/expand of long supporting text

**HSK AI interaction rule:** when collapsed, optional explanatory text is **strictly limited to a maximum of TWO visible rendered text lines** (never three, not even a partial third line), including descriptions only slightly longer than the available area. Show **only one small chevron icon in the upper-right corner** of the explanation container: **⌄** when collapsed, **⌃** when expanded. Tapping it expands or collapses the **same paragraph in place**. **Do not display visible “Подробнее”, “Кўпроқ кўриш”, “Свернуть”, “Йиғиш” or a separate labeled button**, popup, new card, drawer or page. The icon itself is a genuine accessible button with an invisible, localized screen-reader label.

### Eligible content — may be collapsed

- Secondary explanations, optional educational descriptions and extra help **that is not needed to decide or complete the current step**.
- Noncritical supplementary context in cards, tips and settings descriptions.
- When an existing sentence exceeds the available row, allow the disclosure to appear even if the text is only **one line longer** than the compact limit.

### Must remain fully readable — never collapse

- The current **lesson or exercise question**, answer choices, active instruction, essential Hanzi/pinyin/meaning and any information necessary to complete a decision.
- **Payment terms, subscription amounts/durations, renewal conditions, limits and restrictions**.
- Security/privacy warnings, failed-save notices, accessibility guidance essential to completing the step, error details needed for recovery, and mandatory consent text.
- Form labels, required instructions and actual learner-entered text. A free-form textarea must remain editable and must never masquerade as a collapsed description.
- Content that a recognition/translation exercise deliberately hides until its real answer/reveal stage is **not** this disclosure pattern; do not leak hidden answers through the “More” control.

### Exact interaction contract

1. **Hard limit: at most TWO fully visible text lines when collapsed**, regardless of content length, device width, font scaling or language. If the text only occupies one line, show one. Do not leak a third line or a clipped fragment of one. Use a real two-line clamp (PWA: `-webkit-line-clamp: 2` or equivalent robust line limiting; Android Compose: `maxLines = 2` with overflow handling), not a guessed fixed pixel height. Recalculate overflow on layout/font changes.
2. Determine whether the chevron is needed from the **full text measured against the collapsed two-line layout** at the current width, language and accessible font size. **Do not re-test overflow against the expanded layout**: the ⌃ icon must remain available while expanded so the user can collapse the text. After content, width, language or font-size changes, re-evaluate against the two-line limit; if the text now fits, show the whole text with no chevron and clear the expanded state. Place the icon in the **upper-right corner of the same container**, reserving space so it never overlaps either text line. A short description must not show an inert chevron.
3. Expand **in place**, restoring the entire explanation with natural line wrapping, not a popup or scrolling text box. Collapse restores the agreed compact limit without wiping nearby input or learner progress.
4. Render **only the chevron**, not visible text beside or below it. Underneath, use an actual accessible button (not a decorative span): keyboard/touch operable with `aria-expanded`, `aria-controls`, and a localized **aria-label** for expand/collapse on PWA, plus equivalent Android Compose accessibility semantics. Give the icon an adequate invisible touch target (44 CSS px on iPhone PWA; 48 dp on Android), even if the glyph is visually small. The direction **⌄ / ⌃** conveys the state without relying on color.
5. Keep the icon anchored consistently at the **upper-right corner** of the same text container in both states; do not move it below the expanded paragraph. Preserve focus. Ensure changes in height do not unexpectedly move the user's reading position or conceal other actions; honor reduced-motion preferences.
6. Do not truncate semantic content in the saved data. The collapsed state is **presentation only**. On localized font scaling, content replacement and orientation changes, re-evaluate **whether the chevron is needed using the collapsed two-line measurement**, never merely the visible expanded text height. Expanded text must remain selectable and accessible; the chevron remains focusable and in the same top-right position while expanded.
7. For Hanzi/pinyin/translation blocks, only collapse a genuinely **supplementary explanation**. Never cut the learning target or its required pronunciation/meaning merely because it takes two lines.

### Illustrative presentation (noninteractive)

**Collapsed supporting note (MAXIMUM TWO complete lines; never a third):**  
Upper-right corner: **⌄**  
“This word has an additional usage in longer sentences…”

**Expanded in the same position:**  
Upper-right corner: **⌃**  
“This word has an additional usage in longer sentences. It can express a different nuance depending on context and should be interpreted with the full example.”

**No visible text label** accompanies either icon. The localized control name exists only in accessibility semantics. This is a documentation example, not an already deployed HSK AI UI change.

## Learning text hierarchy

| Role | Example | Presentation and semantics |
| --- | --- | --- |
| Hanzi (汉字) | 学习 | Primary learning text when the target is a Chinese word; clear character strokes and a suitable Chinese glyph fallback. |
| Pinyin (拼音) | xuéxí | Directly linked to the relevant Hanzi, in legible Latin characters with **tone marks**. Not a phonetic translation into Russian. |
| Meaning / translation | ўрганмоқ / учиться | A learner-language explanation; choose the actual selected language and context. Do not substitute pinyin for the meaning. |
| Part of speech / grammar note | Verb; usage notes | Secondary to the learning target; keep clear if necessary for the task. |
| Example sentence | 我学习中文。 | Chinese sentence with correct punctuation, optionally with a separately labeled pinyin and translation view. |
| Audio / pronunciation action | Replay pronunciation | A focusable control with a clear label. Audio is an aid, not a substitute for readable text. |

The examples are illustrative content; they are not new lesson records or an instruction to add these words to a live HSK level.

### Hanzi

- Preserve individual strokes; avoid decorative Latin fonts, exaggerated negative letter spacing, automatic uppercasing or transformations that distort Chinese characters.
- Use the product's approved Chinese-capable font stack and allow reasonable glyph fallback where the preferred family is unavailable.
- Prefer an appropriate readable line-height for multi-character words and complete sentences; do not crop descenders, punctuation or large characters inside fixed-height containers.
- Keep simplified Chinese character forms consistent with the actual HSK lesson data; do not automatically change Chinese content between traditional and simplified forms.
- Line breaks may occur between suitable Chinese text units as required, but avoid breaking mixed Hanzi-pinyin-meaning associations so that the meaning of a learning card becomes ambiguous.
- Do not confuse `字` (one character), `词` (word) and `句子` (sentence) in labels or counts.

### Pinyin

- A valid displayed pinyin syllable may contain diacritics such as `ā á ǎ à`, `ē é ě è`, `ǖ ǘ ǚ ǜ`, and neutral tones without diacritics. Keep the **actual stored pronunciation** intact.
- Do not remove tone marks merely to match a font or field width; don't manufacture them from unverified input either. Tone-number forms such as `ni3 hao3` must only be offered where the actual product or exercise supports them.
- Preserve spacing between pinyin syllables and legibility of tone marks when the learner enlarges text. Avoid all-caps conversions and overly tight line-height or clipping.
- If pinyin is hidden as part of a recognition exercise, reveal it only at that exercise's existing answer/review state; this page does not require exposing it in advance.
- Keep any copy and text-to-speech action associated with the correct displayed Chinese entry.

### Meaning and translations

- The user's chosen interface language and the language of a word's meaning must remain consistent with the actual localized lesson content. Do not mix Uzbek, Russian or Tajik fallback strings without indicating which language is being shown.
- Translation length may vary significantly. Permit wrapping in cards, buttons and bubbles; do not silently truncate the **only available** meaning.
- Distinguish a gloss or brief definition from the translation of an entire example sentence. A single word may have several contextual meanings; don't claim a one-to-one translation when the current lesson supplies alternatives.
- Chinese learning tasks sometimes intentionally hide the translation for recall or show it behind a working reveal control. Preserve that behavior.
- Maintain ordinary readable punctuation, numerals and proper names in all supported languages. Latin and Cyrillic fallback must not produce missing glyphs.

## Component-specific applications

### Vocabulary and new-word cards

In the current PWA course, the new-word display uses the order **Hanzi first, then pinyin, meaning and replay**; prominent Hanzi and readable pinyin are the focal elements. Do not transfer these exact fixed sizes to every new screen. Keep its existing animation and lesson state.

### Answer options, listening and tests

The question dictates whether the primary visible text is Hanzi, pinyin, audio or a translation. Do not reveal a hidden answer simply to fill a typography template. Correct/incorrect answer feedback and Panda character reactions retain their existing meaning and motion; typography must not obscure options or be replaced by decorative effects.

### Grammar and examples

Display a full sentence using a suitable Chinese text style. When pinyin and translation are shown, distinguish the three lines visually and semantically. Avoid placing a very long sentence in one unbreakable line, or making the pinyin more visually dominant than the sentence without a task-specific reason.

### AI Voice and conversation

Keep speech transcripts, AI messages, pinyin assistance and any optional translation readable when the keyboard is open, the Orb is active or the screen transitions between voice and chat. Do not copy a fixed-width desktop speech bubble or reveal subtitles/translation that the current voice feature has intentionally hidden.

### Input fields and search

Use the source-derived [Text field](../design-components/text-field.md) guideline for labels, validation, helper text and disabled/read-only behavior. The matching logic for Hanzi, pinyin or translation search must reflect the **actual** supported backend/index; visually displaying pinyin does not prove it is searchable.

## Responsive behavior and accessibility

- Treat the established PWA `px` values as current implementation examples, not mandated typography sizes for the native Android app.
- Do not clip Hanzi strokes, pinyin diacritics, or long localized meanings at 320–360px phone widths, larger device text settings or increased display zoom.
- Keep text legible in both HSK AI themes. Meaning must not depend only on the light/dark accent color or on an unavailable font.
- For accessibility, associate any pinyin and meaning with the correct Hanzi as contextual information. Let the learner read the target without repeating decorative speech-bubble artwork.
- Use clear button labels, visible focus and sufficient tap sizes for audio, show-translation and copy controls. Keep the reading order consistent with the displayed content.
- Test Simplified Chinese characters, marked pinyin, Cyrillic and Uzbek/Tajik special characters in the selected font fallbacks on real iPhone PWA/Safari and native Android.
- An automated layout test may detect clipping, but a language/content review is also needed for tone accuracy and translation meaning.

## Review checklist

1. Is the Hanzi text exactly the content of the authorized lesson or message?
2. Is pinyin correct, readable, tone-marked where supplied and bound to the right entry?
3. Is the translation in the intended learner language and available at the exercise's correct reveal stage?
4. Do the approved UI and CJK font stacks render the necessary glyphs without distortion?
5. Do light/dark theme, narrow screen, keyboard and enlarged text preserve all essential text? Are the type roles consistent and the smallest labels readable?
6. Does the component work with focus, screen readers and audio controls, without changing a lesson's scoring or feedback?
7. Are PWA and Android differences explicitly validated rather than assumed from a shared screenshot?
8. Does the collapsed description display **no more than TWO fully visible rendered lines** at every supported font size and viewport (never a third), with only the top-right ⌄ / ⌃ icon for expanding in place — without hiding a task, question, payment, limit or safety warning?
9. Do one-line, exactly two-line and three-or-more-line texts produce the correct chevron visibility? After expanding, can the user **always tap ⌃ to collapse**? Does resizing, font scaling, changing language or updating content recalculate overflow against the collapsed state without overlapping either line?

## Implementation boundary

This page is a design rule, not a production migration. It does **not** change backend content, scoring, HSK version mapping, fonts bundled in the application, app strings, PWA/Android UI code or the behavior of existing text-to-speech. Any implementation must be reviewed against current real code and learning content first.
