> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/layout.mdx`, Git blob `d936a912a96cc554395de5b4349b9dcf197c506c`; 5 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# Layout

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Source illustration of general layout categories, not HSK AI production UI. Source asset: `./assets/layout/header.png`.

> **Source diagram note:** The retained original wireframes explain the four screen-layout shapes. Their desktop sidebars and two-column geometry are **information hierarchy and density references**, not literal HSK AI mobile layouts. Preserve actual navigation destinations, but use the professional composition to improve the later iPhone PWA/Android interface instead of freezing current appearance.

Layout answers two questions: what kind of HSK AI screen is this, and what is the learner here to do? Each layout type has one primary purpose and a default information density. Choose the type before arranging content. These are information-architecture rules for HSK AI's iPhone PWA and Android, not instructions to copy Khan Academy's desktop page geometry; retain real mobile navigation **function** while improving any weaker visual organization, safe areas, lesson feedback and AI Voice interaction.

## Principles

    
- **One purpose per screen** (Purpose): Every layout type is built around a single user job. When a screen tries to do two things, it does neither well. If content doesn't serve the primary job, it belongs in a different layout.

    
- **Density matches context** (Density): A Job screen should feel minimal. A Reports screen can carry more. The right amount of information is determined by what the layout is for — not by what's available to show.

    
- **Set expectations, then meet them** (Contract): Users associate layout shapes with functions. A screen that looks like a form should behave like one. Surprising users with extra content or unrelated actions breaks the implicit contract.

    
- **Reveal depth progressively** (Disclosure): Detail belongs one level down, not on the surface. Use drawers, modals, and sub-pages to give users more without burdening the primary layout with it.

## Types of layouts

Every HSK AI learner-facing screen maps to one of six layout types. Each is defined by the learner's job, the contexts it's built for, and a default density. Preserve actual mobile navigation destinations and usable bottom-navigation behavior. For the future UI pass, prefer the professional hierarchy, spacing, touch affordances and density over accidental current bar styling; do not copy source desktop side rails literally.

### Dashboard (get an overview and navigate)

A bird's-eye view of the system's current state with entry points to tasks and deeper exploration. Users aren't completing a task here — they're orienting themselves and deciding where to go next.

**When to use:** HSK AI learner home screen, current HSK level/progress overview and entry points to lessons or practice. Admin analytics may use this principle separately, but the learner app must not inherit desktop admin layout.
**Density:** High — users need to scan a lot of information efficiently.

### Learning (learn something new, step by step)

The primary surface where an HSK AI learner actively studies Chinese: lessons, Hanzi/pinyin practice, quizzes, listening, pronunciation and AI Voice conversation. The lesson content is the focus; existing Panda/approved-character reactions and visual effects for both correct and incorrect answers are meaningful learning feedback and must remain. AI Voice retains its approved Orb and interaction states.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Original source Learning wireframe (desktop side rail is not HSK AI mobile layout). Source asset: `./assets/layout/learning.png`.

**When to use:** An active lesson, answer exercise, vocabulary study or AI Voice conversation.
**Density:** Low — the student needs focus. Nothing competes with the content.

### Job (complete a task or fill a form)

A focused flow for completing a task — either a single step or a sequence of steps. The user has one thing to accomplish and the layout clears everything else out of the way. When a task requires multiple sequential decisions, a progress indicator at the top shows the user where they are and how much is left. Complexity is managed by breaking it across steps, not by cramming it onto one screen.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Original source focused task flow (layout principle only). Source asset: `./assets/layout/job.png`.

**When to use:** One-time flows such as account linking, completing a profile action, confirming a purchase or submitting a focused task. Do not copy Khan Academy's teacher/assignment use cases.
**Density:** Low — one task, one focus per step.

### Onboarding (get oriented before starting)

A setup flow for first-time HSK AI learners. New users need clarity above everything else, so each step focuses on the immediate decision without introducing all product features at once.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Original source setup wireframe (its desktop columns must not be copied into HSK AI iPhone onboarding). Source asset: `./assets/layout/onboarding.png`.

**When to use:** First launch, language/HSK-level selection, sign-in, account binding and platform-specific installation onboarding when required. On iPhone PWA, retain the approved Safari/Add to Home Screen guidance rather than a desktop two-column onboarding template.
**Density:** Low — one focus per step.

### Reports (browse or analyze data)

A view for reviewing HSK AI learning progress, completed lessons, results, mistakes and mastery over time. Show verified data, meaningful comparisons and clear next actions; do not mix learner progress with unrelated administrative analytics.

**When to use:** Learner progress and achievement history, mistake review summaries, skill mastery and learning statistics. Admin reports use their own high-density variant without changing the learner app's mobile structure.
**Density:** High — users are here to scan and compare data, so the layout can carry more information than most. The risk isn't too much data — it's data without clear hierarchy.

### Settings (configure or control preferences)

A screen for managing preferences and configurations. Navigation between topics sits above or alongside; the content area handles the active topic. Users come here to adjust something specific and leave — it's rarely a destination in itself.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Original source settings wireframe (not HSK AI mobile navigation geometry). Source asset: `./assets/layout/settings.png`.

**When to use:** HSK AI profile/account settings, language, learning preferences, notifications, privacy and accessibility controls.
**Density:** Medium.

## Compact supporting copy and inline disclosure

For **optional long explanatory text**, do not add an extra popup, card or new page merely to avoid a tall paragraph. Use the [HSK AI inline expand/collapse rule](typography.md): display **at most TWO fully visible text lines when collapsed** in all cases, without even a partial third line (shorter text remains shorter). **Only a small ⌄ / ⌃ chevron appears in the upper-right corner** of the text container when the **full content exceeds two lines in the collapsed layout**; tapping expands/collapses the paragraph **in place**. Keep the top-right ⌃ present while expanded (measure overflow against the collapsed layout, not the expanded one), and reserve space so the icon never covers text. **No visible “Подробнее”, “Кўпроқ кўриш” or “Йиғиш” label.** Provide an invisible accessible name and an adequate touch target.

**Never collapse** the active exercise question, required directions, answer choices, essential Hanzi/pinyin/translation, payment and subscription terms, limits, safety warnings or blocking error details. Those belong in the visible primary content even when they are long. Preserve current page reading order, safe areas, learner progress and approved HSK AI animations.

## Information density

Each layout carries a density contract — a promise about how much the user should expect. Adding content beyond that contract doesn't make a screen more helpful; it makes it noisier.

| Layout | Belongs | Doesn't belong |
| --- | --- | --- |
| Dashboard | High-level metrics, status, navigation to tasks and reports. | Editable fields, long-form content, deep drill-downs inline. |
| Learning | One learning task per step, focused Hanzi/pinyin/content, clear progress and next action, approved Panda answer reactions and AI Voice state when applicable. | Unrelated navigation, several competing tasks or dense reference panels that obscure the active exercise. |
| Job | Only what's needed to complete the action. Fields, instructions, confirmation. | Metrics, related content, contextual tips, "while you're here" info. |
| Onboarding | The single most important thing to understand or do right now. | Full feature explanations, settings, advanced options, edge cases. |
| Reports | Data tables, charts, filters, date ranges. Summary metrics at the top. | Editable fields, task flows, onboarding prompts, unrelated calls to action. |
| Settings | Controls grouped by topic. Labels and descriptions that aid decisions. | Marketing copy, onboarding prompts, unrelated calls to action. |

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/layout/header.png)

- [header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/layout/header.png) — exact source blob `d28b20c3e240` (illustrated above)
- [job.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/layout/job.png) — exact source blob `76bd4840e415`
- [learning.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/layout/learning.png) — exact source blob `117c98f62546`
- [onboarding.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/layout/onboarding.png) — exact source blob `37b779c46c50`
- [settings.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/layout/settings.png) — exact source blob `33402bfa32e5`
