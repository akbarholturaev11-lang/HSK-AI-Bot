> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/popovers.mdx`, Git blob `0ff97d5cb07ece2706aa875bb1b66129ece59957`; 5 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# Popovers

A **popover** is an anchored, non-modal overlay for brief supporting details or small optional actions. The professional anchored-popover anatomy, adaptive placement, focus and dismissal rules are the **design target**. Apply them to HSK AI only where a real feature benefits from a popover and platform constraints allow it; the absence of a current popover is not a reason to erase this professional pattern or claim it already ships.

## When to use

| Use when | HSK AI example |
| --- | --- |
| An existing on-screen control needs concise contextual detail | Clarify a supported lesson-progress status without navigating away. |
| A short feature explanation benefits from proximity to its trigger | Explain a real control during the current screen's supported feature introduction. |
| The user needs one optional action near a related item | Offer a verified existing navigation/action, with a clear destination. |

## When NOT to use

- Long reading, full paragraphs or mandatory notices: keep essential text in the page or use a proper dialog when necessary.
- Destructive actions, payment confirmation, account verification or required input: use the appropriate guarded dialog/screen.
- Active exercise instructions and answers: do not use a popover that obscures a question or leaks a hidden answer.
- Ordinary optional text slightly over two lines: apply HSK AI's **inline two-line collapse** rule instead of a popover.
- A technical problem report or feedback form containing drafts: use the actual submission sheet/dialog and preserve entered information.

## Variants

### Informational

Brief context tied to the triggering element, with optional navigation only if the destination exists. Never invent a score, HSK level, statistic or server state.

### Feature highlight

A short, non-blocking explanation for an available feature. A feature not yet implemented is not a valid live highlight.

### System guidance

An optional nudge associated with a real user flow. If proceeding requires acknowledgement, evaluate a proper dialog instead; do not use a non-modal popover to force critical action. Character illustrations are optional and must use actual approved HSK AI Panda/side-character assets only when the current screen really assigns them.

## Anatomy and actions

- Anchor the overlay to the **actual control** and label the purpose; keep it visually separate from the underlying exercise.
- Prefer a single action. **At most two** for a genuinely small task; if it needs more, use a dialog/screen rather than an overloaded popover.
- Primary actions must describe what actually happens. Acknowledgement only means the user saw the message, **not** that a backend save or lesson result succeeded.
- Do not insert stock mascots, unimplemented awards or external-product promotional art.

## Placement on phones

- Respect the viewport, safe areas, keyboard, active answer options, bottom navigation and AI Voice Orb.
- Prefer above/below the trigger and flip when needed. If anchoring cannot keep controls accessible at the current screen size or enlarged font, use the professionally appropriate bottom sheet or dialog on that phone; preserve the actual functional flow, not the current visual defects.
- Give the popover a sensible maximum size and support natural text wrapping; never force desktop popover dimensions.
- Do not cover essential Hanzi, pinyin, lesson meaning, error recovery or payment conditions.

## Interaction

### Opening

A user-triggered popover should be reachable from a real button and have a clear accessible relationship with its trigger. Product-triggered hints must not appear during unrelated active tasks or disrupt focus.

### Dismissal

A **non-editable, optional** popover can close through its dismissal action, outside tap or platform back/Escape as supported by the current UI. This is **not** permission to discard a typed draft, interrupt a pending request or close a mandatory safety dialog. It never auto-dismisses while someone is reading it.

### One at a time

One popover at a time; a modal/required sheet takes precedence. Do not stack a second overlay over an active exercise answer, login, payment or AI Voice action.

### Focus and accessibility

A user-opened interactive popover should make its controls accessible and restore focus to the opener when closed. Announce relevant status without pulling focus unexpectedly for optional, product-triggered hints. Support touch, keyboard, iPhone PWA and Android equivalents; visible icons require accessible names.

## Restored professional source examples

> **Historical education-product diagrams only.** These examples preserve valuable interaction, composition and state patterns, not HSK AI's actual screens, roles, artwork, data or feature inventory. See the HSK AI-specific rules above before making a production design decision.

### Example 1: popovers

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Original anchored popover overview showing third-party UI, not HSK AI app design. Source asset: `./assets/popovers/popovers.png`.

**Use sparingly:** popovers are attached to existing triggers and only for information or short actions, never for mandatory consent or a long report form.

### Example 2: informational

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Source informational popover for a school learning queue, not HSK AI lesson history. Source asset: `./assets/popovers/informational.png`.

**Informational:** attach the explanation close to its real supported lesson/control, but never cover essential Hanzi, answers or playback controls.

### Example 3: feature highlight

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Original source highlight featuring Gems; no HSK AI Gems feature is implied. Source asset: `./assets/popovers/feature-highlight.png`.

**Feature highlight:** only use when the app actually ships that feature; avoid unsupported reward counters or automated school-task announcements.

### Example 4: system guidance

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Original proctor-themed system guidance; the character and assessment role do not exist in HSK AI. Source asset: `./assets/popovers/system-guidance.png`.

**System guidance:** present brief neutral instructions if they genuinely help the learner. Do not introduce another company's mascot, hint restrictions or user roles.

### Example 5: adaptive anchoring

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Source illustration of an anchored popover that shifts away from the viewport edge. Source asset: `./assets/popovers/adaptive-anchoring.png`.

**Adaptive anchoring:** flip to available space, keep the trigger visible and avoid the keyboard/safe area. Use a professionally composed HSK AI sheet/dialog when a phone has insufficient space, maintaining real actions, focus and draft behavior.

### Interaction details

Opening should come from an actual control, not a surprise during a scored exercise. Prefer only one anchored popover at once. Dismiss via a clear close/outside action only when no unsaved draft or irreversible decision can be lost; retain predictable Escape/back behavior, sensible focus return and adequate touch targets. Long optional descriptions normally use HSK AI's **two-line, top-right chevron in-place expansion**, not a new popover. Historical character figures are never assets to ship.

## Restored popover choice, placement and focus contract

### Select the smallest appropriate overlay

- **Informational:** add concise context or an optional supported action for one visible element. **Feature highlight:** introduce a real currently available affordance, only at a useful moment. **System guidance:** explain an existing step without hiding a required lesson question or leaking an answer.
- Use a tooltip for one short identity label, a dialog/bottom sheet for substantial reading, destructive choices and required decisions, and a banner for global errors. Do not use an anchored popover as a substitute for onboarding a nonexistent feature.
- Character artwork is **optional** and only appropriate when the actual HSK AI learning context already uses that canonical approved character. External mascot/Gem images are structural historical examples, not implementation assets.

### Actions and geometry

- Keep the title concise and the primary action explicit; use one primary action when possible. Never add a decorative “Got it” action as the only way to dismiss urgent or safety-critical information.
- Anchor to the trigger when there is space, but flip or reposition relative to safe-area edges, keyboard and reading direction. On narrow PWA/Android screens, a bottom sheet may be the better semantic presentation; do not copy fixed desktop offsets.
- Avoid blocking the source control or essential current task. Do not let the overlay's caret point to a different element after scrolling, resizing or orientation change.
- Normally show **one popover at a time**. Opening another contextual hint closes the first after state/focus handling rather than stacking inaccessible layers.

### Keyboard and dismissal

- Provide an understandable trigger name, expanded-state semantics and a trigger-to-popover relationship where supported; place focus inside only when the interaction needs it, and restore focus to a meaningful element on close.
- Define Escape/Back, outside press and explicit-close behavior deliberately. If a popover contains a draft or unsent action, accidental outside dismissal **must not discard it** without a safe preservation/confirmation mechanism.
- Support touch and keyboard. A hover-only tooltip or fixed hover timeout is insufficient for a decision-making popover. Announce essential status without repeatedly interrupting screen readers.
- Respect reduced-motion, do not force an illustration animation, and keep controls at the actual PWA/Android minimum interactive sizes.

## Implementation boundary

These are HSK AI interaction rules, not a requirement to introduce a popover library. Existing working **functional contracts**, platform navigation destinations and server-owned state remain authoritative, while the professional popover design takes precedence over today's cosmetic implementation. No foreign character, school reward or assessment examples are product rules.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: popovers.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/popovers/popovers.png)

- [popovers.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/popovers/popovers.png) — exact source blob `afb77135adba` (illustrated above)
