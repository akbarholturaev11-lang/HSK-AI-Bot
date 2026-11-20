---
name: hsk-ai-ui
description: Canonical professional UI/UX design reference router for HSK AI learner iPhone PWA and native Android; source-linked 45-page guideline corpus.
---

# HSK AI UI/UX — professional design system

This is the **existing HSK AI UI skill**, now the single entrypoint for the adapted **45 professional guideline documents** in [references/README.md](references/README.md). Do not reproduce or maintain a competing second set of component rules inside this SKILL.md.

## Mandatory reading order for UI/UX work

1. Read the product root `AGENTS.md` and `AI_RULES.md` for authorization, business logic, Git, privacy, localization, performance and testing constraints.
2. Read [reference index](references/README.md), [professional-first contract](references/PROFESSIONAL_FIRST_CONTRACT.md), and [owner-approved decisions](references/APPROVED_DECISIONS.md).
3. Read [HSK AI product-specific UI/UX contract](references/guidelines/hsk-ai-product-ux-contract.md) to distinguish evergreen UI requirements from approved but unimplemented features.
4. Read **only the relevant detailed guideline files** under [foundations, components and patterns](references/README.md), including the complete visual anatomy, variants, states, spacing, typography, interactions, localization and accessibility conditions.
5. Verify all claimed current functionality against the latest actual PWA and/or native Android source and any relevant current plan. Guidelines and screenshots are not proof of shipped UI.

## Authority and conflict resolution

- **Hard constraints:** real account permissions, privacy/security, accessible interactions, authentic Chinese learning and answer-reveal logic, genuine server-verified payment/Trial/Free/Pro/progress states, native platform capabilities and the actual HSK AI brand, characters and Voice Orb.
- **Visual and interaction target:** the full professional design corpus, preferred over incidental existing styling where it can improve hierarchy, anatomy, alignment, type, consistency, responsive behavior and feedback without violating a hard constraint.
- **Approved product-specific decisions win** over older generic rules for the same narrow scope. Record any evidenced adaptation rather than silently dropping the rest of a guideline. Do not manufacture features, screens, metrics, rewards or payment offers from examples.
- **One disclosure rule:** for genuinely optional supporting descriptions only, use the approved **maximum two fully visible lines + top-right, icon-only ⌄/⌃ expansion in place** from [Typography](references/guidelines/design-foundations/typography.md). The former **One-Line Expandable Text** pattern is superseded and must NOT be reused. Never collapse essential Hanzi/pinyin/meaning, questions, answers, real input, price/renewal/limits, blocking errors or required instructions.
- **One unified layout system:** use the six screen families in [Layout](references/guidelines/design-foundations/layout.md) and the 4-point [Spacing](references/guidelines/design-foundations/spacing.md). Match comparable screen chrome, header/title baselines, horizontal gutters, safe-area edges, content-start anchors, navigation and visual rhythm. **Do not impose one fixed page/content height** on all screen types. Content may grow/scroll; immersive Lesson/AI Voice/checkout flows may have deliberate exceptions.
- **Platform parity is semantic, not pixel-identical:** respect iPhone PWA safe areas/browser/keyboard and Android insets, IME, system Back and scalable dp/sp type; verify concrete widths and interaction states on each platform.
- **Loading/interaction stability:** reuse the product's existing progressive-loading, layout-faithful skeleton and local loading/empty/error/retry contracts, including `docs/PERFORMANCE_PWA_PROGRESSIVE_LOADING.md`; do not create another loading system or blank an unrelated screen.

## Implementation boundary

This skill and its reference Markdown files **do not change the application UI**. Only edit PWA/Android code when the user explicitly authorizes a separately scoped implementation, after inspecting actual code, integration risks and tests. Preserve existing scores, progress, purchases, account state, characters, AI Voice and analytics. Respect localization and accessibility at every step.

**Reference provenance:** These files were transferred from the HSK AI Design System's professional restoration branch as **review drafts**, not certified rights-cleared material. See [references/README.md](references/README.md). Some source-derived prose may require independent re-authoring/permission before public integration; linked example images are source references, not imported production art. Avoid adding vendor fonts, vendor screenshots, Storybook or Wonder Blocks to the app.
