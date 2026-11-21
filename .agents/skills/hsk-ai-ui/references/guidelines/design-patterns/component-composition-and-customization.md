> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-patterns/component-composition-and-customization.mdx`, Git blob `4c8c8dbf0d78a4b20f0e320185ff2ad2f27f5117`; 0 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# HSK AI component composition and customization

> **HSK AI-only adaptation of useful design-system principles previously lost in source cleanup.** These are guidelines for new review work, not evidence that a feature has shipped. The PWA and Android application code takes precedence over this Storybook site. Never use source-school brand assets, roles, scoring semantics or Wonder Blocks requirements as HSK AI instructions.

## 1. Choose a page surface or a Card by purpose

A **task surface** supports a continuous user activity (such as completing an HSK lesson, choosing an answer or reviewing a page). A **Card** groups a distinct object, item, or independently meaningful summary. A whole learning workspace must not be redefined as a nested Card stack simply because a source diagram uses raised boxes.

| Verified implementation | Relevant principle | Avoid |
| --- | --- | --- |
| `app/static/course-v3.html` uses `.wrap`, `.scr`, focused lesson content and persistent `.nav` with safe-area padding | Preserve the learner's main reading/answer surface and navigation anchors | A desktop sidebar or a second elevated panel over the question |
| PWA `app/static/course_v3_data/design-tokens.css` defines `--hsk-paper`, `--hsk-paper-raised`, `--hsk-card-surface` and `--hsk-divider` | Use the existing theme-aware surface and divider roles when a discrete grouping is needed | Historical `semanticColor.core.*` and arbitrary extra shadows |
| Android `android/app/src/main/java/com/pomp/hskai/core/design/Color.kt` defines `PompColors.CardSurface` and platform palette roles | Keep actual Android card/region semantics, touch targets and native navigation | Forcing CSS-style shadows onto Compose or inventing a new theme |

**Decision rule:** first identify the user's task, then the minimal needed container. Prefer an existing component **only when it satisfies the professional visual and interaction standard**; otherwise record the target redesign while preserving its existing functional interface. Propose a shared surface abstraction when task structure and verified reuse justify it, not just because the present UI happens to differ. This documentation alone does not refactor working components; later dedicated PWA/Android redesign may improve their visuals without unnecessarily changing business logic.

## 2. Distinguish layout composition from visual restyling

- Using an existing component's supported props/API for placement, alignment and size is typically a **composition decision**. It must still respect safe areas and **actual functional behavior**, but the existing visual presentation may be improved in the later phase.
- Arbitrary overrides of color, radius, typography, shadows, focus borders, motion, feedback or touch targets are **design-system changes**, requiring actual HSK AI tokens, behavioral review and visual parity evidence.
- A local exception can be valid if its purpose and state are documented, but it is not a new global rule. Avoid old source-specific exceptions and `Wonder Blocks` API names.
- Prefer a native browser/Android control when it communicates the correct task, is accessible and matches actual current app needs. Do not build a custom widget solely because an upstream screenshot used one.

## 3. A control has exactly one semantic job

An icon is not its hit area: keep a meaningful accessible name and adequate tap target, even if the graphic is small. An **expand/disclose** control opens optional content; an **action** control submits or changes state. They must not be conflated as screen width changes.

**The approved optional-description disclosure rule is authoritative:** optional content may collapse to a maximum of two fully visible rendered lines and a top-right ⌄ / ⌃ icon-only toggle with a screen-reader label. Do not hide Chinese questions, Hanzi, pinyin, answer choices, user input, payment terms, critical errors or real purchase status. This page does not redefine that component or add another one.

For new controls follow the actual `.agents/skills/hsk-ai-ui/SKILL.md`: ordinary icon/navigation actions should be flat, without decorative backplates or nested cards; PWA targets are at least 44 CSS px, native Android at least 48 dp. Keep one dominant action per context, immediate local feedback and no duplicate controls.

## 4. Preserve the actual course, cast, Voice and verified outcomes

- `app/static/assets/characters/hsk-character-pack.js` defines Panda, Longlong, Hehe, Wuwu and Yueyue with supported moods. `android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCharacters.kt` maps real card kinds to existing characters and the shared correct/wrong feedback. **Never** import a source-school "exclusive mascot" or a new proctor rule.
- `app/static/iphone-pwa-voice.html` and `android/app/src/main/java/com/pomp/hskai/feature/voice/VoiceV8Orb.kt` have a distinct immersive voice/orb renderer. Its layers, red pearlescent appearance and input keyboard behavior are not generic surface/card treatments.
- `app/static/course_v3_li_onboarding.html`, `app/static/course_v3_data/li-onboarding-runtime.js` and `li-onboarding-install.js` contain the real PWA first-run and Safari install behavior. Generic school onboarding diagrams teach step order, not implementation or a replacement flow.
- Show only server-verified XP, streaks, quiz outcomes, lesson progress, payment rights and analytics. Schematic chart figures from the upstream source do not define HSK AI scores or endpoints.

## 5. When adapting a historical reference

1. Compare the exact idea against current HSK AI `main` source and the current `AGENTS.md`, `AI_RULES.md` and `.agents/skills/hsk-ai-ui/SKILL.md`.
2. Record **observed code behavior**, **reusable general principle**, and **proposed improvement** separately.
3. Keep the principle only if it fits mobile-first, flat-by-default, canonical character/artwork, accurate Chinese learning and server-authoritative states.
4. Reject source brand identity, proprietary assets without confirmed reuse permission, third-party ownership/verdict policy, unrelated rewards and teacher/classroom workflows.
5. Check loading geometry, keyboard, focus restoration, long translations, narrow/large screens, light/dark, reduced motion and platform-native Back. Do not mark any test passed unless executed.

**Source provenance:** Original third-party rulings and examples are inactive evidence under `__docs__/reference-archive/upstream-audit/`; the 120-file, item-by-item reconciliation and real-code conflict notes are recorded in `docs/audits/deleted-material-item-audit-2026-11-15.md`. Neither archive nor historical diagrams have precedence over the actual HSK AI application.
