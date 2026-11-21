> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/text-field.mdx`, Git blob `3a435442dda2c99e9f21f619aa41bc92ae0f0706`; 8 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Text field. Source asset: `./assets/text-field/text-field.png`.

# Text field

> **HSK AI scope:** The eight inherited field illustrations explain labels, placeholders, validation, read-only and disabled states; their school-name examples and source colors are not HSK AI production screens. Preserve the **entire professional text-field design target** (label geometry, state hierarchy, spacing, helper/error treatment, focus and keyboard behavior). HSK AI's current field appearance is a future improvement candidate; adapt only real field content, locale, platform and backend validation requirements.

*Component role: Free-form input*

Text fields allow users to enter and edit text into a UI. They typically appear in forms and dialogs. This is a primary mechanism for gathering user input and data across the platform.

## Recommended: When to use

The choice to use a text field is determined by the need to capture specific, often unique, information from a user during a workflow.

| Use when | Example use |
| --- | --- |
| Capturing a short-to-medium length input where no predefined selection exists | Entering a learner-provided display name or an existing supported lesson note, if the view includes editable text. |
| The user needs to provide a unique detail or description | Providing a short description in an existing HSK AI account or learning workflow, where that field is supported. |
| Defining parameters as part of a multi-step workflow | Entering only the account information that the actual HSK AI sign-in or profile step requires. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| The options are finite and known in advance | Dropdown / select | If there is a finite, known list of options, a text field creates unnecessary typing and potential errors. |
| The user is searching for or retrieving existing content | Search field | Search fields include specific behaviors like "clear" buttons and search icons that standard text fields lack. |
| The input requires multiple lines or paragraph-length content | Text area | Text fields are intended for single lines of text. For paragraphs, use a multi-line text area. The text area is not yet documented in this system; treat this as known design debt. |

## Anatomy

### Standard text field

Label is positioned outside and above the input box. The input box is empty until text is entered.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** A “Username” field shown twice: an empty default field above, and below it the same field in its active state with a text cursor and a darker border. Source asset: `./assets/text-field/states-1.png`.

### Placeholder text

Serves as a brief, transient hint inside an input field to help guide user input. It is best used to demonstrate genuinely required formatting, or clarify an ambiguous expected response. For a Chinese text entry, an example may contain Hanzi or pinyin **only if the field truly accepts that format**. Do not impose US date formatting across HSK AI's supported languages.
Because this text disappears when a user begins typing, it must never replace a persistent external label.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** A “Name” field with the sub-label “Start Description” and gray placeholder text reading “Example: Ms. Z” inside the input. Source asset: `./assets/text-field/states-2.png`.

### Required fields

Use a localized equivalent of "Required" next to the persistent field label instead of an unexplained asterisk. This is more accessible and explicit — users don’t need to find and interpret a legend.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** An “Email” field with a “Required” label inline to the right of the field label, above an empty input. Source asset: `./assets/text-field/states-3.png`.

### Helper text

Used for any helpful description text that would otherwise be hidden in a placeholder. This information is more useful when persistent, and sits below the label and above the input.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** A “Name” field with helper text “This is the name your students see” between the label and the empty input. Source asset: `./assets/text-field/states-4.png`.

## States

### Error

When input is invalid, use the approved HSK AI semantic error color on the field and label together with **specific explanatory text**. Ordinary brand-red primary actions are not the same as destructive or input-error status. Never flag a valid Hanzi, tone mark or Chinese punctuation as an error solely because it is not ASCII.

> **Historical figure 6 — source figure reference (only approved samples, if any, are linked below):** A “Username” field in its error state: red label, a red border around the value “meeeeeeeels@aim.com”, and a red error message below reading “No account found with that username. Please try again or create a new account”. Source asset: `./assets/text-field/states-5.png`.

### Read-only

Displays the current value while explicitly preventing interaction. Unlike disabled, read-only maintains clear color contrast — the content is still meant to be read. Always include helper text explaining why the field is locked, using the current learner's language. Do not hide readable Chinese characters or text merely because the field is read-only.

> **Historical figure 7 — source figure reference (only approved samples, if any, are linked below):** A read-only “Name” field showing “Ema Carinyo” on a shaded background, with a lock icon and the helper text “Only teachers can edit this”. Source asset: `./assets/text-field/states-6.png`.

### Disabled

Used when a prerequisite action has not been fulfilled. The field is grayed out and non-interactive. Once the dependency is met, it no longer displays as disabled. Do not use disabled when read-only is more appropriate — disabled implies unavailability, not restriction.

> **Historical figure 8 — source figure reference (only approved samples, if any, are linked below):** A “Password” field in its disabled state: a grayed-out label above an empty, faintly outlined input that cannot be interacted with. Source asset: `./assets/text-field/states-7.png`.

## HSK AI Chinese and multilingual text-entry rules

### Use the correct input for the task

- Use text fields for **actual supported short answers and profile fields**. Do not introduce a free-text input where HSK AI already has a fixed HSK level, study goal or exercise answer selection.
- Hanzi, pinyin, learner-language translations and usernames are different input types. A field's label, helper text and validation must specify which one is expected. Do **not** claim HSK AI already provides a new dedicated pinyin editor or handwriting engine.
- A pinyin **reading label** in lesson content is normally not an editable field. In any existing editable exercise, match the real backend's supported answer formats before offering input.

### Chinese keyboard and composition

- On supported PWA web inputs, do not validate, submit, trim or transform a partial Chinese IME composition as a finished answer. Handle composition-end before final validation; leave the candidate bar and on-screen keyboard visible and unobstructed.
- Preserve Hanzi, full-width Chinese punctuation and correctly marked pinyin (including tone marks such as **nǐ hǎo**). Do not strip diacritics for appearance or silently equate a tone-marked syllable with its unmarked form.
- Use a readable Chinese-capable font stack for Hanzi, and the approved UI stack with suitable glyph fallback for pinyin and Uzbek/Russian/Tajik. Do not specify a Latin-only source font for Chinese input.
- A copied or pasted value must remain semantically intact; do not mutate Unicode merely to force a design-library demo to match.

### Labels, help, errors and mobile layout

The optional-text disclosure in [HSK AI typography](../design-foundations/typography.md) is for **read-only secondary explanations**, not editable fields. Never collapse entered text, field labels, required helper text, validation errors, password requirements or privacy/payment instructions. Supplementary nonessential descriptions adjacent to a field may use the in-place expand/collapse rule when they really overflow: **the collapsed explanation is limited to MAXIMUM TWO fully visible text lines, with no third-line fragment**, **only a small ⌄ / ⌃ icon in the description container’s upper-right corner**, with no visible label, and with an accessible button name. Preserve the original data and focus during expansion.

- Keep a real field label visible when a placeholder disappears; use concise localization in the app's supported language. Example: **Chinese characters** (汉字), **Pinyin** (nǐ hǎo), **Meaning** (localized), only in contexts that actually ask for those values.
- Match errors to real input restrictions. Explain required versus invalid versus server-failed states without confusing an incorrect exercise answer with a broken form.
- On iPhone PWA and native Android, respect dynamic text scaling, safe areas, selected language length, keyboard insets and accessible focus. Do not make an input unreasonably short to match the source desktop mockup.
- Apply the professional text-field typography, hierarchy and spacing using verified HSK AI semantic color roles where appropriate; do not perpetuate an inferior current style. Consult [HSK AI typography](../design-foundations/typography.md) for Hanzi/pinyin/translation reading order and text roles.

The source screenshots remain **illustrations of form behavior**. This is a design-documentation change; it does not authorize production input or validation rewrites.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: states-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/text-field/states-1.png)

- [states-1.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/text-field/states-1.png) — exact source blob `8822eadf52d0` (illustrated above)
- [states-2.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/text-field/states-2.png) — exact source blob `5bf5878d366e`
- [states-3.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/text-field/states-3.png) — exact source blob `b01cd8d16684`
- [states-4.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/text-field/states-4.png) — exact source blob `25e881708df1`
- [states-5.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/text-field/states-5.png) — exact source blob `411067a6b792`
- [states-6.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/text-field/states-6.png) — exact source blob `9a7c3e32864d`
- [states-7.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/text-field/states-7.png) — exact source blob `116bfd716f05`
- [text-field.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/text-field/text-field.png) — exact source blob `61f9f09e8663`
