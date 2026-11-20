> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/design-components/search-field.mdx`, Git blob `95c5ba716ace3f003d528fdd1f83b99876e1056d`; 5 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

> **Historical figure 1 — source figure reference (only approved samples, if any, are linked below):** Search field. Source asset: `./assets/search-field/search-field.png`.

# Search field

> **HSK AI application:** The source examples illustrate where a search field goes and how it clears; they are not HSK AI school screens. Apply this component only to searchable HSK AI lists that **really exist**. On mobile, keep the field next to the list it affects and preserve the current HSK AI theme and approved icon family.

*Component role: Keyword filtering*

A specialized text input used to accept user-entered keywords or strings to instantly narrow or filter content based on those terms. It is the primary mechanism for finding specific items within large data sets or complex navigation structures.

## Recommended: When to use

The choice to use a search field is determined by the need to efficiently locate specific information that cannot be easily found using predefined filters or navigation.

| Use when | Example use |
| --- | --- |
| The content list contains more than 10–15 items, making visual scanning difficult | Finding a specific vocabulary item in a long recorded word list, if that view offers search. |
| The user is searching by a specific identifier, name, or non-categorical string | Searching for a known Hanzi word or lesson title within a supported HSK AI collection. |
| The dataset is too large for live-filtering and requires explicit submission | Typing a lesson title and submitting to narrow an existing searchable lesson list. |

## Avoid: When NOT to use

| Don’t use when | Recommended alternative | Rationale |
| --- | --- | --- |
| The available options are fixed, small, and mutually exclusive | Dropdown, checkbox, or radio group | Typing to reach one of a handful of known options is slower than picking from them, and it forces the user to guess the exact wording. |
| The user is narrowing a preference with a binary choice | Toggle / checkbox | For a real binary option such as showing only completed lessons, use a toggle instead of a search query when the view supports that option. |
| The input is intended to collect new data, not retrieve existing data | Text field | Search styling promises retrieval. A field that looks like search but stores what the user types misrepresents what the input does. |

## States

### Default / active

The search field is bordered and displays placeholder text like "Search." When active, the input must change appearance to clearly indicate active typing.

> **Historical figure 2 — source figure reference (only approved samples, if any, are linked below):** Two search fields: a default field with a magnifier icon and placeholder, and an active field showing a text cursor and a clear icon. Source asset: `./assets/search-field/default-active.png`.

## Placement

### Contextual placement

The search field must be placed immediately adjacent to the content list or data set it controls. It should never float or sit distant from the elements it is meant to filter.

> **Historical figure 3 — source figure reference (only approved samples, if any, are linked below):** A report page with the search field placed directly above the results table it filters, alongside the other filter controls. Source asset: `./assets/search-field/contextual-placement.png`.

## Interaction

### Clear button

Once text is entered, a clear button (an X) appears inside the field so the user can erase the query without selecting and deleting the text.

Selecting it clears the search term and submits in a single action, restoring results that match any other still-applied filters. This is not an exception to the submission rule — that rule exists to stop results churning on every keystroke, and clearing is one deliberate action. Leaving the results filtered after the field is emptied would show an empty search box above a narrowed list, which states two contradictory things at once.

Focus stays in the field after clearing. A user who clears a search is usually about to type a different one. This differs from Clear filters, where the button removes itself when activated and focus has to be moved deliberately.

> **Historical figure 4 — source figure reference (only approved samples, if any, are linked below):** A search field with a text cursor and a clear “X” button at the end of the input. Source asset: `./assets/search-field/clear-button.png`.

A search term is cleared only from the field. It does not produce an active filter, and Clear filters does not remove it — a user who clears all filters while a search is still applied will see results that remain narrowed by the search term. See [Active filters](active-filters.md) and [Clear filter](clear-filter.md).

## Copy

The placeholder names what the field searches rather than labelling the field. "Search words" or "Search lessons" states the scope; "Search" on its own leaves users guessing whether it covers the table, the page, or the whole product.

Write placeholders in sentence case with no ending punctuation — "Search words", not "Search words…" or "Search."

Where the scope is too broad to carry in a placeholder, pair the field with an adjacent scope selector so the user can see and change what is being searched.

> **Historical figure 5 — source figure reference (only approved samples, if any, are linked below):** A search field whose placeholder reads “Search report,” clarifying its scope. Source asset: `./assets/search-field/scope-clarity.png`.

## HSK AI product application

### HSK AI content and accessibility

- Chinese characters, pinyin and translations are different forms of text. Define exactly which forms the **actual implemented search** supports in each collection; never promise pinyin-to-Hanzi matching or translation search without verifying it.
- Keep the original rule: clearing the typed query restores the result set constrained **only by remaining filters**; it does not silently clear an HSK-level selection, selected date or sort order. Keep keyboard focus in the field and announce updated result counts.
- Use the supported language's concise field label and the HSK AI Phosphor search icon for new ordinary UI. On PWA, the clear button's tap area must be at least 44 CSS px; on native Android 48 dp.
- Search must not discard a partially answered exercise, voice input, saved vocabulary or payment form. When searching is not implemented in a view, this guideline does not require adding it.

## Curated professional visual examples (internal)

These illustrations are retained as **professional reference samples**, not screenshots of HSK AI or evidence that source-specific functions exist. **Apply the design principles; do not copy original brand colors, source metrics, school terms or unverified features as HSK AI requirements.** All image binaries are SHA-preserved in the [approved examples library](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/README.md).

![Professional UI reference: auto-suggestion.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/search-field/auto-suggestion.png)

- [auto-suggestion.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/search-field/auto-suggestion.png) — exact source blob `22ec012e71c7` (illustrated above)
- [clear-button.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/search-field/clear-button.png) — exact source blob `7e437d3d4a7c`
- [default-active.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/search-field/default-active.png) — exact source blob `f7ecf0bdc2a7`
- [scope-clarity.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/search-field/scope-clarity.png) — exact source blob `f6fb0b363183`
- [search-field.png](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/examples/design-components/search-field/search-field.png) — exact source blob `a3021506ac18`
