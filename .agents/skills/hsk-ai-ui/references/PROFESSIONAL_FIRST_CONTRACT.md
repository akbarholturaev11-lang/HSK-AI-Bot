# HSK AI — professional-first design decision contract

**Status:** normative guideline-authoring and future UI/UX evaluation contract. **Not** a feature announcement, implementation instruction or statement that HSK AI already meets all target criteria.

**Scope:** professional guidelines for existing and potential HSK AI **iPhone PWA and native Android** screens. This file is a companion to `AGENTS.md` (which takes precedence for safety and product facts), `DESIGN_SYSTEM_APPROVED_DECISIONS_AND_RESTORATION_TASKS.md` (unaltered owner decisions) and the [45-page historical source reconciliation](docs/audits/professional-rules-source-to-hsk-ai-matrix-2026-11-15.md).

## 1. One-sentence rule

**Use the finest transferable professional UX/UI decision as the default intended design. Keep real HSK AI functionality/identity intact by adapting only the specific collision, not watering down the entire professional component.**

An existing product screenshot, code pattern, or current spacing/color is evidence of *today*, not a reason to choose a weaker design tomorrow.

## 2. Authority and decision model

| Priority | Authority | May change? | Never conclude |
| --- | --- | --- | --- |
| 1. Non-negotiable reality | Legal asset rights, security/privacy/access permissions, accessibility, real platform capabilities, Chinese learning correctness, verified backend and payment status, actual HSK AI canonical character identities and Voice Orb | A design may improve their **presentation**; must not falsify or violate underlying behavior | A pretty example can fabricate a purchase, grade, activity, content, role or feature |
| 2. Professional design system | Transferable component anatomy, information hierarchy, visual proportions, structure, control composition, typography, accessible states, space and motion, placement, patterns and micro-interaction rules | **Preferred standard**; retain all supported detail | The old HSK AI screen has final design veto |
| 3. Product-specific adaptation | Real account/lesson/AI Voice/onboarding behavior, localized content, implemented data fields, PWA/Android touch/keyboard and safe area differences | Adapt **the narrowest necessary point**; document exact reason and target | "Current UI does it differently, therefore drop the professional guideline" |
| 4. Implementation baseline | Existing CSS/Android components, current UI layout, design token names and technical limitations | Candidates for later deliberate **screen-by-screen improvement** | Existing token or visual treatment is necessarily optimal |
| 5. Historical illustrations / demos | Upstream screenshots, sample copy, Wonder Blocks packages and rendered Storybook examples | Evidence of professional reasoning only; may not transfer artwork/third-party product policy without rights | An external vendor screenshot is automatically HSK AI product design or licensed asset |

Where accessibility, authentic brand or functionality conflicts with a particular decorative treatment, **solve the conflict at the smallest level** while preserving the surrounding professional composition. E.g., change only an unsafe contrast pairing, not the entire hierarchy, spacing, icon labeling or alert anatomy.

## 3. Required fidelity — every little design detail

For each component/pattern/foundation, retain what the actual source specifies and mark whether the value is **normative**, **heuristic**, **historical example** or **product-verified**. Never invent numbers; never turn a source-specific example into a universal HSK AI size or token.

### Visual anatomy and composition
- **Purpose and context:** precise task supported, when-to-use and when-not-to-use, priority relative to adjacent elements, alternatives with tradeoffs.
- **Structure:** parent container, heading, eyebrow/caption/description, body, primary and secondary areas, optional controls, separators, footer; semantic and visual order.
- **Geometry:** documented ratios, minimum/maximum widths and heights, padding, gutters, rhythm, alignment, density, edge and corner geometry, optical balance, breathing room; whether values change by viewport.
- **Typography:** type role, weight, line-height, line length, truncation, font fallback, Hanzi/pinyin/tone mark glyph support, learner-language translations and text scaling.
- **Color and elevation:** semantic roles, light/dark surfaces, readable contrasts, scrims, focus indicators, meaning without color, surface separation, motion reduction.
- **Icons and imagery:** purpose, family/weight consistency, size relative to label, hit area vs visible glyph, focus/disabled/selected states; genuine HSK AI brand assets take the place of foreign branding **without erasing the professional structure**.

### Behavior and state machine
- **Entry:** user trigger vs system trigger, availability, disabled/busy/readonly states, focus and keyboard access, platform back.
- **Change:** touched vs hovered vs focused vs pressed vs checked vs expanded vs dragged; how visual state relates to committed server state; pending vs applied values.
- **Exit:** Escape/back/outside tap, Cancel, Apply, Submit, retry, confirmation, dismiss, close; what preserves drafts, undo opportunity and focus return.
- **Loading/result:** initial loading, partial loading, no records, filtered-empty, measured zero, unavailable/unknown data, stale snapshots, error, retry, real success; no ghost-success.
- **Responsive:** narrow 320/375/412-class phone scenarios, large text, expanded Chinese or Russian/Tajik/Uzbek copy, keyboard open, iPhone safe areas, Android insets, orientation, screen-reader order.
- **Motion:** meaningful transition target, easing/continuity, interruption behavior, reduced-motion fallback; preserve character reaction and Voice Orb identity while avoiding fake progress.

### Content integrity and accessibility
- Text first gives truthful state/action, secondary help does not obscure the task, no hidden payment terms, question, options, user input or Hanzi/pinyin/meaning.
- Long **optional supporting descriptions** only: maximum two **fully visible rendered lines** collapsed; the top-right icon-only **⌄/⌃** expands to full in-flow copy; visible label absent, assistive label and proper activation present. This is an approved HSK AI interaction exception, **not** a replacement for all professional disclosure/dropdown/popover patterns.
- iPhone PWA accessible targets **at least 44×44 CSS px** and Android targets **at least 48×48 dp**. Preserve the professional icon's visible dimensions and spacing where possible; add invisible hit area if necessary rather than enlarging all glyphs.
- Hanzi → tone-marked pinyin → selected-language meaning is a **learning content hierarchy**, not a mandate that every unrelated analytics summary or settings control display three text rows.

## 4. What HSK AI compatibility actually means

**Functional invariants to preserve:** current navigation destinations; lesson start/check/answer reveal; completion and retry; correct AND incorrect character feedback; AI Voice listening/thinking/speaking behaviors and red pearlescent Orb; authorized analytics ownership/grain; server-verified Pro/payment/subscription state; safe onboarding and Safari PWA installation behavior; localizations; Android/PWA capability differences. Verify per code before calling something implemented.

**Brand invariants:** authentic HSK AI Chinese-knot logo, approved Panda, Longlong, Hehe, Wuwu and Yueyue artwork and their state meanings, original Voice Orb, real semantic palette and brand identities. **Brand identity does not freeze all current UI color applications, icon alignment, card shapes, contrast or component layouts.** Professional design can improve those.

**What is not an exception:** "We already use a different card border", "the existing modal is less polished", "this spacing value occurs in CSS", "the source image has school content", "we do not currently support this chart". The first three are future design gaps; the last two require neutral reference treatment or an unimplemented label, **not deletion** of transferable professional rules.

**No feature inflation:** documentation may specify the ideal design of an available interaction, or keep a generic professional pattern as reference. It must never create new app features, flags, backend fields, monetization schemes, scores, achievements or navigation destinations by assumption.

## 5. Micro-detail coverage map — do not lose the professional decisions

Use this table as the minimum page-by-page review contract. The named documents are existing guidelines, not claims that each behavior already exists in the HSK AI app.

| Guideline(s) | Retain professional detail | Only legitimate HSK AI adaptation |
| --- | --- | --- |
| `design-components/buttons.mdx` | Primary/secondary/tertiary hierarchy, count, visual balance, size, placement, icon/text, focus/press/busy/disabled/exit state, destructive action hierarchy | Actual supported actions, functional commitments, mobile target size, brand colors |
| `badges.mdx`, `banners.mdx`, `toasts.mdx` | Severity, icon and copy, feedback persistence, action priority, stacking, duration, dismissal, progress/outcome semantics | Real account/lesson/payment states; no fictitious success or unsupported reward |
| `text-field.mdx`, `search-field.mdx` | Label, helper, placeholder, invalid state, field grouping, keyboard, focus, clear behavior, copy and error specificity | Supported fields and Chinese/translation input; keyboard and safe area |
| `checkbox-group.mdx`, `radio-button.mdx`, `toggle.mdx` | Single vs multiple and on/off semantics, selected/disabled/read-only, grouping, density, affordance, immediate vs deferred commits | Only actual options; don't invent settings or student filters |
| `dropdown-select.mdx`, `modals-selection.mdx`, `inline-filter-button.mdx` | Accessible selection states, overlay anchoring, option hierarchy, applied vs draft selection, Apply/Cancel, scroll and focus | Actual dataset fields, existing permission checks, phone sheet vs dropdown |
| `active-filters.mdx`, `clear-filter.mdx`, `date-filter.mdx`, `date-picker.mdx`, `design-patterns/filter-and-sort.mdx` | Search/filter/sort separation, progressive controls, scope, date semantics, clear/reset, empty results, control placement and responsive density | Verified real query parameters and defaults; user-localized labels/dates |
| `modals.mdx`, `popovers.mdx`, `tooltips.mdx` | Overlay taxonomy, scrim, z-index, adaptive anchor, content length, focus entry/restore, Escape/back/outside tap, action count, interruptibility | Real high-stakes flows, phone safe area and keyboard, inline optional help exception |
| `progress-stepper.mdx` | Linear vs nonlinear stages, sequence legibility, compactness, accessible current step, stable placement | Actual verified onboarding or task sequence; no fictitious step count |
| `chart-container.mdx`, `summary-cards.mdx` | Header/measure/support/controls/data hierarchy, independent widget states, scope/denominator and freshness, informative titles | Actual verified analytics data, permission and platform coverage |
| `progress-charts.mdx`, `trend-charts.mdx`, `distribution-charts.mdx` | Chart-form selection, true zero, missing vs zero, plot anatomy, axes, comparison, bands, marks, legend, shape and colors, exact accessible table | Real recorded measures and real goals, never school scores or fake mastery scale |
| `data-tables.mdx`, `design-patterns/data-reports.mdx` | Records vs summary, sort/filters, cell density, pagination/scroll, responsive alternative, error and empty page/container distinction | Permissions, event data source, anonymization and supported actions |
| `design-foundations/colors.mdx`, `colors-semantic.mdx`, `borders-and-dividers.mdx` | Semantic intent, contrast, layering, divider rhythm, edge hierarchy, error/focus/selection separation and theme completeness | Actual brand accent, approved tokens and verified light/dark roles |
| `design-foundations/typography.mdx`, `spacing.mdx`, `layout.mdx` | Complete typographic scale, rhythm, hierarchy, baseline, readability, six task layouts and adaptive composition | Pinyin/Hanzi/selected language, actual screen task and platform insets; the existing layout is **not** final authority |
| `design-foundations/surfaces-and-elevations.mdx`, `motion.mdx` | Layering, task surface vs item card, shadow, elevation, blur, transitions, time/easing intent and reduced motion | True voice orb / lesson character animations, HSK brand depth and supported device interactions |
| `design-foundations/iconography.mdx`, `illustration.mdx`, `design-components/hsk-ai-characters.mdx` | Icon grammar/optical alignment, illustration roles, timing and meaningful guidance, state fidelity, placement | Phosphor generic icons, official HSK character identities and canonical originals only |
| `design-patterns/collecting-feedback.mdx` | Entry point, short/long feedback choice, draft preservation, attachments consent, selection, submission acknowledgement | Actual supported feedback channels and verified server outcome |
| `design-patterns/component-composition-and-customization.mdx` | Composition, variation boundaries, task surface vs card, use the right abstraction before bespoke UI | Real HSK features and visual identity; never enforce old Wonder Blocks SDK |
| `design-patterns/professional-reference-gallery.mdx` | Source professional spatial/structural evidence and granular rationales | Historic image must remain clearly non-product and **not assumed rights-cleared** |
| `introduction.mdx` | Global design philosophy and implementation expectations | Exact function/brand exceptions and phased future handoff |

**Coverage rule:** the historic source contains **45 original MDX documents**, with **3 vendor-exclusive pages excluded** and **2 HSK AI-only additions**, resulting in **44 active docs**. A prior page-by-page [reconciliation matrix](docs/audits/professional-rules-source-to-hsk-ai-matrix-2026-11-15.md) records each disposition. Do not claim full parity merely from this checklist: consult the actual page text and the historical reference for details before removing or rewording any rule.

## 6. Mandatory exception register

Every substantive divergence must be recorded where it occurs, using:

> **Professional default:** exact applicable design guideline, with geometry/state/interaction detail.  
> **Evidence:** historical page/figure, HSK AI code path or approved owner decision; state what was **observed**, not inferred.  
> **Conflict:** precisely which feature/brand/platform/data/security constraint prohibits literal use.  
> **Minimal adaptation:** the smallest substitute that keeps professional intention, anatomy and behavior.  
> **Fidelity preserved:** the details retained despite substitution.  
> **Status:** (a) existing app today; (b) professional target; (c) not implemented/illustrative.  
> **Future UI/UX delta:** which screen later needs visual or interaction work (no implementation in this phase).

**Prohibited vague justifications:** "HSK AI style is different", "old screenshots are not ours", "only keep what is already implemented", "not applicable", "too complex" or "there's no test", without the specific contextual reason. These statements are not a license to remove the underlying professional technique.

### Owner's image-handling clarification — internal professional examples

The owner specified **no publication** and a simple visual distinction: **retain/migrate useful generic sample illustrations that teach component anatomy or design decisions, exclude real screenshots of other apps and vendor business screens.** Judge the actual image, not its filename or the fact that it is historical. Selected examples remain **illustrative** and do not change the official HSK AI brand palette/spacing/functionality. Preserve every transferable professional micro-detail from an excluded screenshot in the surrounding design text.

The source contains many different image types; do not call every PNG a foreign screen, or drop a valid neutral reference image on that basis. For documented visually verified examples and the remainder's `REVIEW_REQUIRED` handling, use [visual reference selection](docs/migration/VISUAL_REFERENCE_SELECTION.md). There is no public-site publication in the current plan; source rights statements should be accurate but cannot substitute for the user's selection criteria.

## 7. Publication / artwork provenance boundary

A rule or generic anatomy description can be retained and rewritten; historical third-party PNGs must not be assumed licensed because they exist in git. **Keep source-figure identity separate from design-guideline completeness.** If redistribution rights cannot be shown, the professional geometry and reasoning stay in text or a newly rights-cleared original schematic; historical source-only visuals must not be published as HSK AI artwork.

Documentation source comparison and rule completeness can be reviewed **without** running app build/device tests. A later public Storybook deployment still warrants its own build and asset review, but lack of a CI run is not evidence that the written design **decision hierarchy** is wrong or incomplete.

## 8. Handoff — only after the guideline work is approved

**Separate future phase: real HSK AI interface redesign audit, one screen at a time.** First inspect actual current `HSK-AI-Bot/main`, taking iPhone PWA and native Android as the only implementation targets. For each screen:

1. Identify its real task, UI tree, user role, localized texts, app state/route, server ownership and live interaction contract.
2. Compare it **micro-detail by micro-detail** with this professional design contract and the relevant existing MDX pages: layout, proportions, typography, card or surface, actions, iconography, focus, animation, all empty/busy/error states and device adaptations.
3. Record **current → professional target → justified functional exception**; the professional rule wins aesthetic disagreements unless blocked by a hard constraint.
4. Implement in separately approved, reviewable phases with real product tests at that time, preserving backend, subscription, authentication, lesson correctness, telemetry and accessibility. Changes to PWA and Android should be feature-parity-aware but respect genuine platform differences.
5. Do not introduce new product functionality just to fit a professional screenshot; do not disguise an unsupported feature as implemented.

**No production application files are modified by this contract.**
