# Selective OpenSpec for HSK AI

OpenSpec is an **optional spec-driven planning layer**. It does not replace
`AGENTS.md`, `AI_RULES.md`, `PROJECT_MEMORY.md`, scoped handoffs, existing
skills, CI tests, or the repository's branch/deployment policy.

## When to use

Use a proposal for substantial cross-platform features, architectural or
database changes, new modules with multiple consumers, and high-risk changes to
identity, authorization, subscriptions, payments, or course entitlement flows.

Do **not** require it for cosmetic UI, a single isolated bug fix, copy edits,
routine documentation, or a task whose accepted scoped handoff already gives a
complete implementable plan. Continue working from the existing plan in those cases.
Never backfill old finished features just to populate `openspec/specs/`.

## Codex setup and workflow

Requires Node.js >= 20.19.0 and the official OpenSpec CLI. On a developer
machine, once per environment:

```bash
npm install --global @fission-ai/openspec@latest
openspec --version
# Optional: install official upstream Codex workflow skills:
openspec init --tools codex
```

The repository already provides a scoped Codex entry-point skill:
`.agents/skills/hsk-ai-openspec-planning/SKILL.md`.
It can be invoked as `$hsk-ai-openspec-planning` in Codex or selected in Skills.
After official initialization, OpenSpec also offers `$openspec-propose`, etc.
Both must respect the opt-in scope above; neither overrides repository rules.

For a NEW qualifying feature, inspect code and current feature handoff, then:

```bash
openspec context --json
openspec new change <kebab-case-name>
openspec status --change <kebab-case-name> --json
openspec instructions proposal --change <kebab-case-name> --json
# Write proposal as instructed, then specs, design and tasks in CLI dependency order.
openspec status --change <kebab-case-name>
```

An agent must use the live CLI-generated artifact instructions and never invent
`.openspec.yaml` scaffolding or pretend the plan was validated. `openspec
validate <change-name>` applies to a populated change, not an empty scaffold.
Implementation remains under the normal Codex/repository Git and test rules.
If a feature already has an active handoff, link the proposed delta to it rather
than establishing a second canonical tracker.

## Scope and safety

- Planning artifacts under `openspec/changes/` are *proposals*, not proof of code
  completion or approval to change production.
- All product invariants and localization rules continue to apply.
- No runtime dependency, database migration, service, UI, secrets, feature flags,
  or production deployment is introduced by this integration.
- CI only verifies the OpenSpec planning scaffold; product test suites are
  still mandatory when product code changes.
- Official documentation: https://github.com/Fission-AI/OpenSpec
