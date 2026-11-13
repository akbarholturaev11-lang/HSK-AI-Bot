---
name: hsk-ai-ui
description: Concrete HSK AI learner PWA and Android UI/UX design standards: hierarchy, consistent characters, mobile interactions, accurate per-section skeletons and progressive disclosure.
---

# HSK AI UI/UX — concrete design standards

Scope: user-visible design and interaction patterns for learner **iPhone PWA and Android**. Use these rules when creating, modifying or reviewing an HSK AI screen. Keep this skill UI/UX-only; general engineering, API, analytics, monitoring, CI, release and Git rules belong in \`AGENTS.md\` and the relevant project documents.

## 1. Unified screen alignment and vertical rhythm

- Screens of the same category use consistent header height, title baseline, back/action icon positions, top inset, horizontal gutters and first-content start position.
- Navigating between ordinary screens must not cause headers or navigation anchors to visibly jump. Account for platform safe areas and keyboard insets.
- **Do not force all pages to have the same content height.** Let content scroll naturally; focus on aligned chrome and stable anchors. Immersive AI Voice/full-screen flows may follow their own deliberate layout.

## 2. No unnecessary icon or button backplates

- Default utility/navigation icons to a clean visual treatment **without a decorative card, tile, icon backplate, extra border, repeated background or shadow** behind them.
- Avoid wrapping a button inside another button-looking card. Keep one legible control, not multiple ornamental layers.
- A filled primary CTA, an intentional selected/active state or a meaningful semantic control background is allowed. Do not remove useful affordances or shrink tap targets to make the UI appear flatter.

## 3. Flat by default, no visual overload

- Render ordinary settings, navigation, facts and lists as simple rows, spacing and dividers by default. Use a card only where it actually groups a distinct interactive task, progress block or meaningful content.
- Avoid nested cards, excessive glass, multiple borders/shadows, competing bright colors, decorative badges and constant glow.
- Give visual prominence to the current learning task and relevant CTA rather than to decoration. Preserve an intentional immersive background (e.g. AI Voice) where it serves the feature.

## 4. Concise user-facing copy

- Never show internal system explanations, backend/API/database terminology, debug codes, implementation details or long developer-style descriptions on learner screens.
- Prefer a short title and an actionable, plain-language sentence only when needed. Do not add explanatory copy solely to fill space.
- Preserve material user-facing information: actual limits, payments/renewal conditions, critical errors with recovery, and essential lesson/question instructions must remain clear and accessible.
- Long **optional** hints follow the dedicated One-Line Expandable Text pattern below; do not conceal essential facts.

## 5. No duplicate UI; one clear primary action

- Do not display duplicate controls for the same action, repeat the same statistic in adjacent sections, or add redundant Back/Close/Cancel/Save entry points without distinct purpose.
- Each context should have one visually dominant primary action; secondary actions remain available but quieter. Do not make two competing primary CTAs.
- Interactive controls must have clear affordances and distinct selected, loading, disabled and error states. Decoration must not look tappable.

## 6. Consistent design language and platform parity

- Reuse established HSK AI colors, typography, spacing, radii, icon style and existing component patterns instead of inventing new variants on every screen.
- Keep the same information hierarchy, primary task and interaction logic across PWA and Android; allow platform-native controls, safe-area differences and appropriate gestures rather than pixel-for-pixel imitation.
- Preserve existing HSK AI visual identity, including the purposeful use of the cinnabar/red accent and the established iPhone PWA Liquid Glass navigation behavior. Special-purpose experiences (such as AI Voice) may have distinct presentation without breaking usability.
- Chinese learning UI must make Hanzi, pinyin and translation legible **when each is pedagogically appropriate**; do not reveal a quiz/flashcard answer before the intended interaction.

## 7. Canonical character identity — mandatory visual consistency

- **The same named HSK AI character must have the same recognizable identity everywhere it appears**: silhouette, face/eyes, ears, body proportions, characteristic colors, accessories and illustration style. Do not invent a new panda face, proportions, fur style or unrelated mascot for a new screen, loading state, campaign or feature.
- **Panda remains the established Panda character** across onboarding, course, lessons, voice and other Panda appearances. Only the pose, gesture, facial expression, gaze, reaction, movement or scene composition may change as appropriate to context. Those changes must not make it look like a different panda.
- If another existing cast character is explicitly used, preserve **that character's** canonical identity too; do not silently replace every pre-existing character with Panda. Existing web character pack: \`app/static/assets/characters/hsk-character-pack.js\`; Android character source: \`android/app/src/main/java/com/pomp/hskai/core/design/components/HskCharacters.kt\`. Other currently used Panda renderers include \`feature/course/PandaMascot.kt\` and \`feature/onboarding/OnboardingPandaMascot.kt\`.
- Reuse existing approved character artwork/rendering as the visual reference. Where multiple renderers already exist, compare their actual appearance and converge toward the established persona instead of drawing a speculative replacement. Do not treat a generated image that merely resembles a panda as matching the HSK AI character.
- Characters are contextual teachers/companions, not mandatory decoration on every statistics row, control or loading slot.

## 8. Progressive disclosure without extra surfaces

- Show the information necessary to understand and complete the current task immediately. Reveal optional secondary explanations in place only on demand.
- Avoid opening an entire sheet/page/modal simply to expand a short hint. Do not add decorative expand buttons, duplicate labels or a second card.
- For a one-line expandable helper, follow the exact One-Line Expandable Text specification below (do not invent a different “Подробнее” pattern).

## 9. Motion with a purpose

- Use animations to explain a transition, feedback, status or user gesture — not as competing decorations. Prefer restrained motion; keep reading and next actions available.
- Preserve the app's intentional smooth AI Voice orb transitions and other meaningful interactive animations; avoid persistent motion on routine cards or lists.
- Respect reduced-motion preferences. Use motion only where a static state would be less clear, not to cover layout instability.

## 10. Exact layout-matched skeletons and independent reveal — mandatory

**Design the loading state from the populated component, not from a generic placeholder.** This is a visual/interaction contract; implementation mechanics are governed by \`AGENTS.md\` and \`docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md\`.

1. **Exact geometry:** each skeleton matches its own actual content area at the relevant screen width — outer box, minimum height, padding, margins, gaps, column structure, text line slots, imagery/avatar dimensions, aspect ratios, border radii and alignment. The same screen type may need responsive presets. Do not use a generic skeleton card or spinner where the actual UI has a different composition.
2. **Keep known UI visible:** titles, section labels, tabs, fixed nav, known field labels, static icons and other content **not dependent on the request** render immediately in their final position. Skeleton shapes cover **only unknown, not-yet-loaded data** (for example name, score, remote image, list rows, quota). Do not replace a known label with a gray bar.
3. **Independent sections:** each data-dependent component owns its own loading/ready/empty/error presentation. If a screen has 10 independent sections and 3 have finished loading, show those 3 immediately in their final slots; the other 7 keep their own skeletons. Do not hold a finished section behind the slowest request or replace the whole screen with one shared loader.
4. **In-place settlement:** once verified data for a section becomes available, replace only that section's skeleton **inside its reserved geometry**. Already visible sections, header and bottom navigation must not jump or be remounted visually. A short opacity cross-fade (~150–250 ms) is acceptable; **do not animate the entire screen height or shift neighbouring content**. With reduced motion, replace instantly.
5. **Realistic variable-content design:** provide bounded/known-size text slots, stable rows, line wrapping rules and image aspect ratios when those can be established. Truly unpredictable content cannot be guaranteed pixel-exact before retrieval: reserve the stable visible structure and let overflow grow inside a suitable scroll/content area without shifting fixed anchors. Never clip essential lesson, price or warning text merely to claim zero layout shift.
6. **Local error/empty/retry:** a failing section presents its own compact, meaningful error/empty state and recovery action in the same area while successfully loaded siblings stay visible. Do not imply an unloaded result is zero, complete or successful.
7. **Visual review:** compare skeleton → partial data → fully loaded at narrow, normal and large mobile widths on both PWA and Android, including long translations, slow/failing sections and reduced motion. Check top/header/nav and surrounding section anchor positions; any visible jump is a design defect to investigate, not something to disguise with shimmer.

## 11. Honest UI states, readability and accessibility

- Show real verified values only; distinguish \`loading\`, \`no data\`, \`unavailable/error\` and verified \`0\` visually. Do not fabricate XP, streak, score, rank, Pro rights or a completed lesson for presentation.
- Ensure readable contrast, clear focus/selection feedback, meaningful labels, and sufficiently large touch targets (PWA ≥44 CSS px; Android ≥48 dp) even where icon artwork is visually small.
- Support long Uzbek/Russian/Tajik labels, Simplified Chinese, large font settings, wrapping and mobile widths without clipped core actions. Important statuses cannot rely on color alone.

## One-Line Expandable Text — UI/UX standard

Apply this presentation to **non-essential helper text, secondary descriptions, and explanatory hints** in HSK AI learner PWA and Android. Match the established Admin PWA interaction in `app/static/admin-pwa/app.js` (`foldHints`, `toggleHint`) and `app/static/admin-pwa/styles.css` (`.hint-clamp`, `.hint-fold`) visually; implement with the appropriate native controls for each platform rather than importing Admin PWA code.

1. **Collapsed by default:** show at most **one rendered text line**, with an ellipsis (`…`) when the text overflows.
2. **Conditional indicator:** only when the text actually overflows, show a small, unobtrusive **chevron-down** (`⌄`) at the right edge. If the full text fits on one line, show no chevron and do not present an expand control.
3. **In-place expand:** tapping either the truncated text or the chevron reveals the **entire text in the same location**; the indicator becomes **chevron-up** (`⌃`). Tapping again collapses it to one line. Never navigate to a new screen or open a modal for this.
4. **Minimal presentation:** no `Подробнее` / `Свернуть` labels, additional buttons, decorative cards, icon backplates, borders, shadows, or extra background surfaces. The text and chevron form one accessible interaction target.
5. **Motion:** use a subtle 150–250 ms expansion/collapse transition without abrupt jumps or blocking the interface. Respect the system's reduced-motion preference.
6. **Accessibility:** make the interaction keyboard/screen-reader operable, expose its expanded/collapsed state, and preserve a usable touch target (**at least 44 CSS px on PWA / 48 dp on Android**) without making the visual chevron oversized.
7. **Do not truncate essential content:** lesson explanations required to answer, question/answer text, instructions, critical feedback, payment prices/terms, limits, error recovery, or important safety notices must remain fully understandable without expanding a hint. Apply this pattern only where optional detail can safely be hidden.

**Review check:** test short vs overflowing text, very narrow screens, long UZ/RU/TJ translations, large text settings, expanded/collapsed state, and reduced motion. Avoid applying a one-line clamp indiscriminately to all text elements.
