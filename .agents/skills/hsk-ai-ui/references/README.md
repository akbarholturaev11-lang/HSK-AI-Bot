# HSK AI — UI/UX professional design references

**Scope:** learner iPhone PWA and native Android. This directory is the documentation corpus used by the existing `hsk-ai-ui` skill. It is NOT application runtime, does not authorize a feature by itself, and does not override security, payment, localization or teaching rules in product `AGENTS.md`.

**Source:** `akbarholturaev11-lang/HSK-AI-Design-System`, branch `restore/hsk-ai-professional-unified-audit-20261115`, as accessed on 2026-11-20. The original 44 portable professional rules and one HSK AI-specific supplement are retained, rather than inventing a second independent design standard.

## Read in this order

1. [Professional-first contract](PROFESSIONAL_FIRST_CONTRACT.md) and [approved HSK AI decisions](APPROVED_DECISIONS.md).
2. [HSK AI product-specific UI/UX contract](guidelines/hsk-ai-product-ux-contract.md).
3. [Introduction](guidelines/introduction.md) and only the applicable foundation, component and pattern documents listed below.
4. Current product `AGENTS.md`, `AI_RULES.md`, real platform-specific source and performance/localization policies before implementation.

**Precedence:** safety, privacy, accessibility, verified Chinese-learning content, legitimate user/account/payment states, platform capabilities and canonical brand assets remain hard constraints. For visual design, professional full-detail rules improve incidental present-day UI. A guideline/roadmap is not proof a feature was implemented. Preserve existing data and flows until separately authorized implementation and regression tests.

**Important publication/reuse status:** 44 professional files are source-derived internal review drafts with historical upstream-prose licensing not yet fully established. This import records those source drafts; it does not certify redistribution rights or final visual parity. **Do not merge or republish these verbatim documents as rights-cleared release material until provenance and permission/re-authoring is reviewed.** Historical example images and vendor fonts are NOT copied into the app. Links to neutral source examples point to the original design repository for review only and are not production dependencies.

## 45 guideline pages

- [HSK AI learner UI/UX contract (45th HSK-specific supplement)](guidelines/hsk-ai-product-ux-contract.md)
- [Introduction](guidelines/introduction.md)

### Design foundations — 11

- [borders and dividers](guidelines/design-foundations/borders-and-dividers.md)
- [colors semantic](guidelines/design-foundations/colors-semantic.md)
- [colors](guidelines/design-foundations/colors.md)
- [data visualization](guidelines/design-foundations/data-visualization.md)
- [iconography](guidelines/design-foundations/iconography.md)
- [illustration](guidelines/design-foundations/illustration.md)
- [layout](guidelines/design-foundations/layout.md)
- [motion](guidelines/design-foundations/motion.md)
- [spacing](guidelines/design-foundations/spacing.md)
- [surfaces and elevations](guidelines/design-foundations/surfaces-and-elevations.md)
- [typography](guidelines/design-foundations/typography.md)

### Design components — 27

- [active filters](guidelines/design-components/active-filters.md)
- [badges](guidelines/design-components/badges.md)
- [banners](guidelines/design-components/banners.md)
- [buttons](guidelines/design-components/buttons.md)
- [chart container](guidelines/design-components/chart-container.md)
- [checkbox group](guidelines/design-components/checkbox-group.md)
- [clear filter](guidelines/design-components/clear-filter.md)
- [data tables](guidelines/design-components/data-tables.md)
- [date filter](guidelines/design-components/date-filter.md)
- [date picker](guidelines/design-components/date-picker.md)
- [distribution charts](guidelines/design-components/distribution-charts.md)
- [dropdown select](guidelines/design-components/dropdown-select.md)
- [hsk ai characters](guidelines/design-components/hsk-ai-characters.md)
- [inline filter button](guidelines/design-components/inline-filter-button.md)
- [modals selection](guidelines/design-components/modals-selection.md)
- [modals](guidelines/design-components/modals.md)
- [popovers](guidelines/design-components/popovers.md)
- [progress charts](guidelines/design-components/progress-charts.md)
- [progress stepper](guidelines/design-components/progress-stepper.md)
- [radio button](guidelines/design-components/radio-button.md)
- [search field](guidelines/design-components/search-field.md)
- [summary cards](guidelines/design-components/summary-cards.md)
- [text field](guidelines/design-components/text-field.md)
- [toasts](guidelines/design-components/toasts.md)
- [toggle](guidelines/design-components/toggle.md)
- [tooltips](guidelines/design-components/tooltips.md)
- [trend charts](guidelines/design-components/trend-charts.md)

### Design patterns — 5

- [collecting feedback](guidelines/design-patterns/collecting-feedback.md)
- [component composition and customization](guidelines/design-patterns/component-composition-and-customization.md)
- [data reports](guidelines/design-patterns/data-reports.md)
- [filter and sort](guidelines/design-patterns/filter-and-sort.md)
- [professional reference gallery](guidelines/design-patterns/professional-reference-gallery.md)

**Integrity target:** 45 Markdown guideline pages = 11 foundations + 27 components + 5 patterns + 1 introduction + 1 HSK AI supplement. The two authority documents above are supporting records, not duplicate guideline pages.

**Scope of this transfer:** only design documentation and the existing skill's routing. No PWA, Android, backend, checkout, lesson, XP, permissions, state, analytics or asset code was changed.
