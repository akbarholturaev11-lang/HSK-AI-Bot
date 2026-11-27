> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/progress-stepper.mdx`, Git blob `fcc32708dcf3fdf4466426f4270466d1fbfe5f8c`; 4 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Progress stepper. Source asset: `./assets/progress-stepper/progress-stepper.png`.

# Progress stepper

> **HSK AI scope:** The original images illustrate the principle of showing position in a defined sequence, not HSK AI's branded interface. Preserve the complete professional stepper hierarchy, rhythm, label density, visible progress states and placement as the target; retain authentic Panda assets and actual platform/onboarding behavior, but allow today's mobile layout to improve in the later UI pass. Do not force this component onto login, a loading screen, a payment return or a one-step preference action.

*Component role: Multi-step flow*

Communicates a user's position within a multi-step, sequential flow, signaling how much of the process remains. Two variants exist based on flow complexity and page context.

## Recommended: When to use

The choice to use a progress stepper is determined by the need to guide a user through a defined sequence of steps where order matters and progress visibility reduces abandonment or errors.

| Use when | Example use |
| --- | --- |
| The flow has several defined, ordered steps (typically 3–6) | An actual HSK AI first-run study setup or another verified sequential action with multiple decisions |
| Steps are sequential — each one leads to the next, whether it requires input or is informational | A supported sequence in which the next learning choice depends on a previous choice, such as the actually available course track and level |
| The flow has a clear, known endpoint | A sequence that ends at a confirmed saved preference or verified course entry, never merely at an unconfirmed network request |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| Steps can be completed in any order | Checklist or task list | A stepper implies sequence. Non-linear tasks create confusion about whether order is enforced. |
| 2 steps or fewer | Single-page form or modal | A stepper adds structural overhead that isn't justified for minimal flows. |
| The system is doing the work, not the user | Loading state | A stepper implies user-driven advancement. System-driven progress needs a different pattern. |

## Variants

### Simple

Segmented bars + numeric counter. No step labels. These are visual indicators only, they are not clickable to navigate between.
Use for lightweight, motivational flows like onboarding where steps don't need to be named.

On a full-screen HSK AI onboarding flow, place the indicator where the professionally composed mobile task layout supports clear progression, without covering the primary button, safe area or keyboard. The source's bottom-left desktop placement is a reference rather than a mandatory phone position.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Variants 1. Source asset: `./assets/progress-stepper/variants-1.png`.

### Complex

Named steps with completion indicators and a progress underline. 
Use when steps have distinct names, the flow is task-critical, or a user may need to navigate back to a previous step.

For HSK AI's truly task-critical sequential flows, keep the named stages in a stable, visible place that suits the professionally designed phone navigation and the actual flow. The source's centered top desktop position does not override iPhone or Android safe areas.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Variants 2. Source asset: `./assets/progress-stepper/variants-2.png`.

## Copy

Applies to step labels in the complex variant only.
Keep labels to 1–2 words, favoring a single word whenever it stands on its own — reach for two only when one word isn't clear enough. Labels should name the stage rather than instruct the user. Many words work as both nouns and verbs (Review, Order) — that's fine as long as the label reads as the name of the step, not a command ("Review," not "Review & assign"; "Order", not "Set order"). Write in sentence case.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Copy. Source asset: `./assets/progress-stepper/copy.png`.

## HSK AI onboarding and account safety

- Do not impose the source's typical 3–6 steps on HSK AI's existing longer, branching or platform-specific first-run paths. Only show progress for the current **actual ordered decision sequence**, with an honest count and endpoint.
- A returning verified learner may directly enter the course; don't invent onboarding progress for steps that were already completed or do not apply to this account.
- On iPhone PWA, the Safari installation guide is an optional platform instruction shown according to the existing browser-mode/session logic, not a new required numbered learning step. On Android, do not insert an iPhone installation step.
- Verification, asynchronous loading, Pro entitlement checks and redirects are **system states**, not steps the user completes. A wait spinner must not advance the step indicator.
- The simple indicator is informational and non-clickable. Named stages can support returning to completed decisions only if the specific HSK AI flow permits it; never jump across a required verification, purchase or owner-boundary check.
- Retain the original guidance on short, understandable step names and stable placement. **Additionally for HSK AI**, provide an accessible description of the current step and total number of steps when known; do not announce every decorative animation. Follow the approved HSK AI touch targets, localization and reduced-motion behavior. Do not alter production UI in a documentation-only update.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/progress-stepper/copy.png)

- [copy.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/progress-stepper/copy.png) — exact source blob `320fb8cfa6dd` (illustrated above)
- [progress-stepper.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/progress-stepper/progress-stepper.png) — exact source blob `c6595be449f0`
- [variants-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/progress-stepper/variants-1.png) — exact source blob `7f478a31e99a`
- [variants-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/progress-stepper/variants-2.png) — exact source blob `0442c9a9d456`
