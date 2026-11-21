> **HSK AI professional guideline — standalone internal review draft.** Source `__docs__/introduction.mdx`, Git blob `89d1fba1d56431f8bc801d3753e951ed61c6804c`; 0 historic figures, 0 MDX interactive demos. Only selected neutral example PNGs, if any, are included below; excluded foreign screens and vendor runtime were not transferred. Source prose remains an internal draft; omitted historical figures are not claimed visually equivalent. No live HSK AI feature is implied.

# HSK AI Design System

This is the **HSK AI** design guideline library for the **iPhone PWA** and **native Android** learning application. It is a reference for decisions about learning layouts, typography, accessible interactions, user feedback, reporting and artwork. It is **not** the application source or proof that a proposed feature has shipped.

## Professional-first design decisions

**The professional design system is the preferred design target.** It determines component hierarchy, visual anatomy, density, alignment, spacing rhythm, typography, states, micro-interactions, accessibility, feedback and responsive presentation. The current HSK AI PWA/Android interface establishes **which functions really exist and what their behavior/data/brand constraints are**, but it does not automatically determine the best visual solution. If the existing screen is weaker, **the screen is the later migration candidate — not the guideline**.

Transfer the original professional detail intact wherever its reasoning is reusable. Adapt only the narrow point that clashes with **verified HSK AI functionality or server semantics**, the real HSK AI brand/characters/Voice Orb, language-learning integrity, mobile platform behavior or security/accessibility. Do **not** inherit source schools, Gems, badges/currency, mascot or proprietary assets. If no comparable HSK AI feature exists, preserve its professional rule as a **non-implemented reference**, without claiming an app feature exists.

For exact decision hierarchy, exceptions, micro-detail fidelity and the later implementation handoff, see [Professional-first decision contract](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/DESIGN_SYSTEM_PROFESSIONAL_FIRST_CONTRACT.md). The **next phase**, after these rules are approved, is a separate **screen-by-screen PWA/Android UI/UX refactor against the documented professional standard**. This phase does not modify product code.

## Authority and scope

- Read the repository-root **`AGENTS.md`** before applying any guideline in Codex or another coding agent.
- The HSK AI product code in `akbarholturaev11-lang/HSK-AI-Bot` (current `main`) is the **read-only source for verifying actual behavior** during documentation work. A design proposal is not the same as an implemented function.
- Product priorities are mobile PWA and Android, Chinese learning with Hanzi/pinyin/translation, approved Panda and other lesson characters, verified exercise results, the red AI Voice Orb and server-authoritative account/Pro state.
- The design guidelines do **not** mandate features, characters, theme settings, scoring policies or engineering libraries from another company.

## How these guidelines are structured

**Foundations** define HSK AI's semantic colors, typography, responsive layout, spacing, elevation, motion, illustration and iconography. Use [Typography](design-foundations/typography.md) for Hanzi/pinyin/translation and the **maximum two-line inline disclosure** of optional supporting text.

**Components** describe purpose, usage boundaries, interactive states and accessible presentation for real learner or authorized-admin interfaces. The [HSK AI characters](design-components/hsk-ai-characters.md) page defines the actual Panda and supporting cast, and distinguishes them from the AI Voice Orb.

**Patterns** cover combinations of components, including data reports, feedback, filters and onboarding. Some pages document **proposed guidance** and are not a claim that the product has already implemented every option.

## How Codex should use this documentation

1. Start from `AGENTS.md` and a relevant guideline rather than scanning old package names for policy.
2. Verify HSK AI's **current actual platform implementation** before changing UI. Do not assume PWA and Android have identical flows.
3. Only apply guidelines that fit the requested screen, its verified backend, localized text and existing design semantics.
4. Keep learning content readable and correct. Preserve hidden-answer rules, progress ownership, correct/incorrect feedback and accessibility.
5. Never implement or reintroduce former Khan Academy mascots, school workflows, Gems, rewards or source scoring thresholds.
6. When a source-themed illustration or legacy demo component remains for documentation rendering, it is **not an HSK AI product specification**.
7. Report test coverage accurately. A successfully updated markdown file is not equivalent to an actual Storybook build or device validation.

## Development and preview

This project is a **Storybook documentation site**, not a reusable production UI package. Some technical authoring/rendering dependencies retain their original package names; that does not make their product rules authoritative.

The repository's `package.json` currently offers `pnpm start` (local Storybook, default port **56789**), `pnpm build` and `pnpm typecheck`. Run these in a configured local workspace or CI before claiming that the docs compile. Do not use an external site's MCP address as this HSK AI project's official endpoint.

## Updating guidelines

Keep professional reasons, visible states, accessibility and actual product constraints. Remove unsupported brand examples, obsolete instructions and dead links rather than preserving a contradictory history. Any app-code implementation requires its own review and approval outside this design repository.
