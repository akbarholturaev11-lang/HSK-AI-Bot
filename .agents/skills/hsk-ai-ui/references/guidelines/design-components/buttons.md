> **HSK AI professional design guideline — portable review copy.** Current implementation is not implied. Source `__docs__/design-components/buttons.mdx` (Git blob `b20a71a3783cba8a21797b4a431a696ea57d6c92`); 16 historic figure references, 12 MDX demo blocks. Approved neutral example PNGs are linked below where available; excluded foreign screens and vendor runtime code were not transferred. The original prose remains an internal source-derived draft. Full professional prose is retained as an internal source-derived draft.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Buttons. Source asset: `./assets/buttons/buttons.png`.

# Buttons

> **HSK AI scope:** The original figures and live demonstrations illustrate professional button hierarchy and states, **not** HSK AI's final colors, branded button styles or screens. **Preserve the full professional button visual/interaction hierarchy as the redesign target.** Keep only real HSK AI action semantics, brand identity and mobile platform constraints; the current button appearance is not the design standard. This documentation does not change production code.

  
*Component role: Call-to-action/Interaction trigger*

A button is a discoverable interactive element that starts a specific action. HSK AI retains the original professional action hierarchy and predictable interaction semantics across iPhone PWA and Android. Source demonstrations are not its visual branding.

## Recommended: When to use

The choice to use a button is determined by the need to prompt the user to perform an action that changes the state or context of the system.

| Use when | Example use |
| --- | --- |
| The action is the primary goal of the current view | Save, Submit, Confirm — the main thing a user needs to do on this screen. |
| The action has a clear, immediate outcome | Start lesson, Check answer, Save preference, Confirm a real purchase. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| The action is inline within a body of text | Text link | Buttons interrupt reading flow. Inline actions should use a text link. |
| The action switches between independent, persistent views (site sections, main nav) | Tabs or nav link | Buttons imply an action with an outcome. This is site navigation, not a task action — different from moving through steps within a single flow (see Tertiary button). |
| The outcome is revealing options, not executing an action | Dropdown or overflow menu | A button implies something will happen immediately. If the result is showing more choices, use a dropdown or menu pattern instead. |

## Variants

### Primary button

Used for the single most important action on the page—the one that completes the workflow (Submit, Start) and drives the user toward the main goal. Use only one primary button per page.

A modal, drawer, or other overlay is its own context, so it can have its own primary action. The primary button on the page behind the scrim doesn’t count as a second one.

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: button primary: Primary button.

> **Avoid demo:** put a primary button on every card when the page already has a primary action.. **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Variants 1. Source asset: `./assets/buttons/variants-1.png`.

### Secondary button

Used for an intentional alternative action that creates value (Save draft, Duplicate).
Can be used multiple times on a page if actions are of equal importance.
Don’t use it for navigation or low-value trivial actions (View details, Preview).

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: button secondary: Secondary button.

> **Avoid demo:** use secondary buttons for low-value actions like “View course” repeated down a list.. **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** Variants 2. Source asset: `./assets/buttons/variants-2.png`.

### Tertiary button

Used exclusively for low-priority actions that change the state on the current screen. Do use for actions that abandon or exit the current workflow (cancel, exit, close), for simple movement backward or through a defined flow (previous, back, next step), or for actions that branch into an optional setup or preference setting (customize, advanced settings). This is flow navigation — advancing through steps within a single task — not the page-level navigation described in "When NOT to use"; switching between independent, persistent views should still use Tabs or a nav link.
Avoid styling links as buttons (e.g., a "Read more" button). To maintain accessibility and meet user expectations, designers and developers must ensure each is coded correctly: links go places, while buttons do things. Confusing these functions breaks core navigation logic and creates significant barriers for users with disabilities.

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: button tertiary: Tertiary button.

> **Avoid demo:** use a tertiary button for “Read more.” It takes the user somewhere, so it should be a link.. **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** Variants 3. Source asset: `./assets/buttons/variants-3.png`.

### Neutral button

Neutral tokens help preserve hierarchy balance when multiple kinds of elements with differing visual weights are present in a view. Single-use icon buttons — like an X (close), a back button, or an info icon — should be neutral, not the primary action color. Our current application of them is for icon-only tertiary buttons.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** Three icon-only neutral buttons: an X (close), a back chevron, and an info icon. Source asset: `./assets/buttons/neutral-icon-buttons.png`.

Use neutral text buttons where the **professional hierarchy** calls for a low-emphasis action; repair a weaker current HSK AI hierarchy in the later app-redesign phase rather than lowering this standard. Source-team approval procedures are not HSK AI policy.

> **Avoid demo:** The historical example assigns the neutral action color to primary, secondary and tertiary text buttons, obscuring the intended hierarchy. For HSK AI, preserve professional contrast and neutral-icon rules without banning justified low-emphasis text actions.. Example UI: button primary: Primary button; button secondary: Secondary button; button tertiary: Tertiary button.

### Destructive button

Use for destructive or irreversible actions, such as account deletion. The distinct Critical color must not be confused with HSK AI's ordinary brand-red non-destructive primary action. Never use Critical red for normal lessons, purchases or harmless retries.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** States 3. Source asset: `./assets/buttons/states-3.png`.

## Sizing

### Default buttons

Use the complete professional button anatomy, shape, emphasis, spacing rhythm and state behavior as the target; reuse existing components only when they meet it, otherwise record a future visual delta. Retain HSK AI's documented 4-unit spacing compatibility. Minimum interactive areas: **44 × 44 CSS px on iPhone PWA** and **48 × 48 dp on Android**; the visible icon can be smaller than its hit area. Do not invent arbitrary production dimensions.

### Small buttons

Small buttons are low-emphasis UI elements used for supplemental actions that must remain accessible without competing with the primary focus of the page. They are essential for maintaining a clean visual hierarchy in tight spaces or high-density interfaces, ensuring that complex or information-dense layouts remain scannable and uncluttered.
Space is constrained: Ideal for actions nested within confined areas like cells (e.g., UMG work), list items, or small cards where a standard button would feel bulky.
Hierarchical balance is needed: Helps avoid "button fatigue" when prominent primary or secondary CTAs are already present, allowing the user to focus on the main task while keeping utilities available.
Utility-based actions: Perfect for "micro-actions" within a larger workflow, such as table column headings that trigger modals, linking accounts in settings, or batch actions like "Select All."

> **Illustrative demo:** A **small-size tertiary button**, sourced from a variant marked `size="small"`, is a visually compact micro-action. Its interactive hit target still meets the relevant iPhone PWA / Android accessibility requirement.

> **Recommended demo:** use a small button for a micro-action inside a compact card, like “Set reward.”. **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** A small 'Set reward' button used inside a compact Gem challenge card. Source asset: `./assets/buttons/states-1.png`.

### Width

By default, buttons should hug their content — sized to fit the label plus consistent padding, never wider than necessary. Full-width is the exception, not the default, and should be used deliberately.

**Mobile and narrow viewports:** On mobile or in single-column layouts (forms, modals, bottom sheets), stretch the primary action to full-width. This gives it a larger, easier-to-hit target and reinforces it as the clear next step in a constrained space.

**Desktop and wide layouts:** Avoid full-width buttons on desktop unless the button lives inside a narrow container (a sidebar, a card). A full-width button in a wide layout reads as visually heavy and can look like an error state rather than an intentional choice.

**Grouped buttons:** When multiple buttons appear together (Cancel / Save), keep them hug-width and let them sit side-by-side — full-width only applies when a single button occupies its own row.

Don't stretch a button to full-width just to fill unused horizontal space. Width should communicate intent — this is the primary, unmissable action — not just close a layout gap.

## States

### Disabled

Use disabled buttons in cases when you need to prevent a user from acting on items where the action is functionally impossible or forbidden, such as a "Submit" button when previewing an activity.
Don’t use a disabled button to communicate when conditions for progressing or successfully taking action are not met.

> **Illustrative demo:** A **disabled primary button** (source sample includes the Boolean `disabled` state) remains visibly inactive and must not submit anything. Disabling a button solely because the learner has not yet completed an optional prerequisite is the distinct anti-pattern shown next.

> **Avoid demo:** disable a button because the user hasn’t finished a step yet, like selecting questions to review.. **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** States 4. Source asset: `./assets/buttons/states-4.png`.

### Loading

Use a visible loading state and protect against duplicate submissions while an asynchronous action is pending. The label and accessible status should explain what is happening; on failure provide a real recovery route. Never treat an unconfirmed purchase or unsaved lesson as successful.

## Iconography

Do use an icon if the icon symbolizes the result or category of the action and the icon conveys the same meaning as the text in milliseconds. This helps improve its clarity.Omit if the button works just as well without the icon.
Icon placement: Icon set to “start” is to indicate action, emphasis, and category. Icon set to “end” indicates status, direction, or change in context. 
Icon-only buttons: Do use them only for universally understood actions (search, settings, close, edit) And use the Neutral action (not Progressive/the default color).

> **Historical figure 9 — source figure reference (only approved samples, if any, are linked below):** States 5. Source asset: `./assets/buttons/states-5.png`.

## Special cases

### Buttons for HSK AI learning

In lessons, one next action leads the current step: **Start lesson**, **Check answer** or **Continue**. Answer options are learning selections rather than independent competing primary actions. Keep the existing correct/incorrect Panda and approved-character facial reactions, gestures and animations. Icons and accessible labels complement those effects, never replace them.

### Pro and subscription actions

A purchase or confirmation can be the primary action in its own context. Retain the approved Pro crown, gold and payment presentation. The backend's verified payment state—not a bank authorization or browser redirect—determines successful access. Never create a source-product Gem currency or an unavailable payment path.

### Achievements and utility actions

XP, streaks, HSK progress and rewards are information until a real destination or claim exists. The same button hierarchy applies to settings and administrative screens. Reuse approved HSK AI assets and the accepted Phosphor family for ordinary new UI icons.

## Placement

### Priority placement

The Primary button should be placed in the most visible and logical position for the user's flow (e.g., block-end of a form or modal).

> **Historical figure 10 — source figure reference (only approved samples, if any, are linked below):** Placement 1. Source asset: `./assets/buttons/placement-1.png`.

### Hierarchy and grouping

If bundled together, the actions should be ordered from lowest priority to highest priority. This helps ensure that the final decision the user makes is the most important one.
Group related actions together. In a modal or form, the order should generally be: [Secondary: Cancel/Back] followed by [Primary: Submit/Save].

> **Illustrative demo:** Historical visual example (not a shipped HSK AI component). Example UI: button tertiary: Tertiary button; button secondary: Secondary button; button primary: Primary button.

**When there are too many buttons:** Cap a visible button group at two, occasionally three, when every action genuinely needs equal prominence (Cancel / Save / Save and close). Beyond three, the group stops reading as a hierarchy and starts reading as a list of options.

**Rule of thumb:** If a user has to scan more than three buttons to find the one they want, buttons aren't helping them decide quickly anymore — that's what a menu is for. Consolidate the lower-priority actions into a dropdown or overflow menu, and keep only the single most important action as a standalone button.

## Copy

### Brevity

Aim for 1-3 words. The text must be immediately scannable.

> **Historical figure 11 — source figure reference (only approved samples, if any, are linked below):** Copy 3. Source asset: `./assets/buttons/copy-3.png`.

### Action focus

Button copy must be short, clear, and focused on the action (a verb or a verb phrase).
Avoid technical jargon or vague labels like "OK" or "Click Here". Use clear action verbs like "Save Changes" or "Next Step".

> **Historical figure 12 — source figure reference (only approved samples, if any, are linked below):** Copy 1. Source asset: `./assets/buttons/copy-1.png`.

### Labels stand alone

Button labels must be a single action phrase. Descriptive or explanatory text must not appear inside a button.
Buttons communicate an action, not context. If users need more information before acting, provide it through helper text, tooltips, or a confirmation dialog — not inside the button label itself.

> **Historical figure 13 — source figure reference (only approved samples, if any, are linked below):** Copy 2. Source asset: `./assets/buttons/copy-2.png`.

### Sentence case

To be consistent with UX copy guidelines, use sentence case.

> **Historical figure 14 — source figure reference (only approved samples, if any, are linked below):** Copy 4. Source asset: `./assets/buttons/copy-4.png`.

### Punctuation

Do not use periods, question marks, or exclamation points at the end of button text. Button text is typically a fragment, phrase, or command, not a full sentence, and terminal punctuation adds unnecessary visual clutter and reduces scannability.

> **Historical figure 15 — source figure reference (only approved samples, if any, are linked below):** Copy 5. Source asset: `./assets/buttons/copy-5.png`.

### Consistency

Always use logically paired verbs for opposite actions, as the choice clarifies the type of movement. Previous / Next is used for simple, non-committing pagination through lists or sequences. Back / Next or Back / Continue is used for advancing through procedural flows like multi-step forms or wizards. Never mix terms from different pairs (e.g., avoid "Previous/Continue").

> **Historical figure 16 — source figure reference (only approved samples, if any, are linked below):** Copy 6. Source asset: `./assets/buttons/copy-6.png`.

## HSK AI verification safeguards

- One main action per interaction context; a separate dialog may have its own primary action.
- Ensure actions do not obscure Hanzi, pinyin, answer choices, keyboard, safe areas or AI Voice controls.
- Test correct/incorrect learning feedback, loading, accessibility, press states and duplicate-request protection on both mobile platforms.
- Keep existing brand-red versus Critical semantics, 4-point spacing tokens and approved custom icons. Source screenshots are educational references, not product artwork.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: buttons.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/buttons.png)

- [buttons.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/buttons.png) — exact source blob `5cecea5ba49e` (illustrated above)
- [copy-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/copy-1.png) — exact source blob `968df7d58547`
- [copy-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/copy-2.png) — exact source blob `618926f46a01`
- [copy-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/copy-3.png) — exact source blob `af6317f468cc`
- [copy-4.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/copy-4.png) — exact source blob `e28b6738fafa`
- [copy-5.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/copy-5.png) — exact source blob `4c7531905a6d`
- [copy-6.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/copy-6.png) — exact source blob `00970245c302`
- [header.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/header.png) — exact source blob `6b7a2a8eb962`
- [neutral-icon-buttons.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/neutral-icon-buttons.png) — exact source blob `6343332a32cc`
- [states-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/states-2.png) — exact source blob `06fbddaf9c81`
- [states-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/states-3.png) — exact source blob `188531c139ad`
- [states-5.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/states-5.png) — exact source blob `de73c05c75df`
- [variants-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/variants-1.png) — exact source blob `6e8045edf0dc`
- [variants-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/variants-2.png) — exact source blob `310d8293a021`
- [variants-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/buttons/variants-3.png) — exact source blob `43dbb1eb6cf6`
