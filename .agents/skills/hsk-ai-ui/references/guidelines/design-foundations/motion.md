> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-foundations/motion.mdx`, Git blob `55d96973acd95eb568d0d4f2edf8698f8c17e099`; 6 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Motion. Source asset: `./assets/motion/motion.png`.

# Motion

Motion helps HSK AI learners understand what is happening: where a screen is going, what is loading, and whether an answer was correct or incorrect. Motion clarifies interaction rather than adding constant decoration. Established Panda and other approved-character reactions to both correct and incorrect lesson answers are purposeful learning feedback, not decorative motion to remove. Milestone celebrations and the red pearlescent AI Voice Orb are other intentional expressive-motion contexts.

## Principles

    
- **Motion earns its place** (Purposeful): Every animation should help the user — orient, confirm, or guide. If removing it doesn't confuse anyone, remove it.

    
- **Snappy, not sluggish** (Fast): Every user is between tasks, not settling in to watch an animation. Default durations should feel quick. Motion that holds up the interface is motion that fails.

    
- **Respect reduced motion** (Accessible): Honor prefers-reduced-motion system settings. Motion should complement the interaction, never dominate it — transitions that are smooth and subtle by default, never the most noticeable thing on screen.

    
- **Motion clarifies, never carries** (Foundational): An experience should be fully understandable without animation. Motion shows where you came from, where you're going, or what just changed — but it should never be the only way to communicate it.

## Exceptions

Three HSK AI contexts intentionally allow expressive motion: immediate lesson answer reactions, meaningful learning milestones, and the AI Voice Orb. Character reactions and celebrations should play briefly once and settle; the AI Voice Orb may move continuously while Listening, Thinking or Speaking is active. All must respect reduced-motion preferences and never block lesson actions.

### Panda and approved-character answer reactions

The existing HSK AI Panda and other approved lesson characters MUST continue to react to BOTH correct and incorrect answers, using their established facial expressions, gestures, poses and related effects. Correct-answer reactions should communicate success; incorrect-answer reactions should acknowledge the mistake clearly and support retry or learning without ridicule. Provide an immediate, brief reaction that settles without delaying the next answer or blocking the next action; avoid repeating or looping routine feedback. Preserve canonical character identity and existing effects across PWA and Android. Use readable success/error cues alongside motion so answer correctness is not conveyed by animation or color alone.

### Student celebration moments

When a learner completes a lesson, reaches a verified milestone, or earns a genuine achievement, a richer celebration, confetti or a reward reveal is appropriate. Keep these moments special. This limitation on *large celebrations* does NOT prohibit short, existing Panda/character reactions and feedback effects after each correct or incorrect lesson answer.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Student celebration motion example. Source asset: `./assets/motion/exceptions-2.png`.

### AI Voice Orb

The existing red pearlescent HSK AI Voice Orb preserves its approved three-dimensional glow and Listening, Thinking and Speaking motion. Unlike routine character reactions, the Orb may animate continuously for as long as the corresponding voice state is active. Its transitions must remain smooth, must not obstruct conversation/controls, and must offer a reduced-motion alternative that still communicates state.

## Usage guidelines

### Transitions

Use motion to communicate spatial relationships — panels that slide in from the side they originate from, drawers that expand from their trigger.
Keep transition durations short. Most UI transitions should feel nearly instant.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Drawer transitioning in from right to left. Source asset: `./assets/motion/usage-guidelines-1.png`.

A drawer transitioning in, coming in from the right to left.

### Loading states

Show a skeleton screen rather than a spinner whenever the shape of the content is known.
Use a spinner only when duration is truly unknown and no structural preview is possible.
Never use a fake or non-reflecting progress bar. If real progress can't be measured, use indeterminate states honestly.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Skeleton loading state of the learner class dashboard page. Source asset: `./assets/motion/usage-guidelines-2.png`.

Skeleton loading state of the learner class dashboard page.

### Intentional loading states

Some loading states should be deliberately crafted to reflect the weight of what's happening — not just fill technical wait time. This builds trust. In moments like these, the loading state is part of the experience, not a workaround for latency.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Intentional loading state example. Source asset: `./assets/motion/usage-guidelines-3.png`.

### Animations

Trigger routine animations in response to a real state change, a learner action, or viewport entry — not as arbitrary recurring decoration. Preserve the established correct/incorrect answer feedback effects; after a brief character reaction, settle into the appropriate readable feedback state rather than looping. Ordinary decorative animations should finish promptly and generally stay under 5 seconds; do not delay the learner's next action. The active AI Voice Orb is the explicit exception to the no-looping and short-duration rules, because its continuous motion communicates Listening, Thinking or Speaking. Support reduced motion for every category.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** Animation example. Source asset: `./assets/motion/usage-guidelines-4.png`.

## Accessibility

All motion in the product must respect the `prefers-reduced-motion` media query.

| Default behavior | Reduced motion behavior |
| --- | --- |
| Slide transition | Fade or instant |
| Expand/collapse animation | Instant show/hide |
| Correct/incorrect answer reaction | Static character expression with persistent correct/incorrect text and icon |
| Celebration animation | Simplified or static |
| AI Voice Orb | Minimal/static state indicator, preserving Listening/Thinking/Speaking meaning |
| Loading skeleton pulse | Static skeleton |

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: motion.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/motion/motion.png)

- [motion.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/motion/motion.png) — exact source blob `ccd36c0b2e2d` (illustrated above)
- [usage-guidelines-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/motion/usage-guidelines-1.png) — exact source blob `38862df9f3b1`
- [usage-guidelines-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-foundations/motion/usage-guidelines-2.png) — exact source blob `0361cbde5519`
