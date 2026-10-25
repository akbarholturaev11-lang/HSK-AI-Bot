---
name: hsk-ai-openspec-planning
description: "Selective OpenSpec planning for high-risk or cross-platform HSK AI changes. Use when planning new modules, database/architecture changes, auth, payments, entitlements, or multi-client behavior; do not use for minor UI edits or routine bug fixes."
---

# HSK AI · selective OpenSpec planning

This skill adds a **planning overlay only**. `AGENTS.md`, `AI_RULES.md`,
`PROJECT_MEMORY.md` and relevant feature-scoped handoffs remain authoritative.
It is NOT permission to refactor implementation, overwrite product decisions,
merge, deploy, or mark tests as passing.

1. **Eligibility first.** Prefer the existing quick Codex workflow for minor
   UI/copy, isolated bugs, documentation, or fully scoped current handoffs. Use
   OpenSpec only for high-risk/cross-platform/new-module changes or when the
   user expressly asks for an OpenSpec proposal. Do not convert all work.
2. **Source audit.** Read current `AGENTS.md`, `AI_RULES.md`,
   `PROJECT_MEMORY.md`, the relevant active feature handoff, and real
   code/tests. Identify actual branch HEAD, external consumers, preservation
   rules, failure modes, and what must remain outside scope. Avoid competing
   progress files. Reconcile differences with the canonical handoff.
3. **Use the actual CLI.** Check `node --version` (>= 20.19.0) and
   `openspec --version`. If missing, use the documented official CLI install
   method if allowed in the current environment; if unavailable, report the
   blocker, do not fake successful OpenSpec generation.
4. **Resolve project.** Run `openspec context --json` and read
   `openspec/config.yaml`. Stop on unresolved/wrong root. Never initialize
   another project accidentally.
5. **Create a change when truly needed.** Run `openspec new change "<slug>"`
   (for an existing change, inspect it instead), then
   `openspec status --change "<slug>" --json`. For each necessary artifact
   in dependency order, run
   `openspec instructions <artifact-id> --change "<slug>" --json`;
   use its returned path, template, context, dependencies and rules.
   Never manually invent the scaffold or assume an artifact's shape.
6. **Plan only.** Specify real current contracts, affected paths and clients,
   failure/rollback approach, bounded acceptance criteria and test matrix.
   Link to the existing handoff rather than cloning it. Do not implement
   runtime code as a side effect of choosing this skill.
7. **Verify honestly.** Re-run status and use `openspec validate "<slug>"`
   once artifacts are populated; explicitly distinguish CLI validation from
   running app tests or physical device/staging acceptance. Handoff to the
   ordinary Codex implementation workflow only when user authorization for
   implementation exists, following the current Git/QA policy.

Do not use OpenSpec to weaken existing security, authorization, billing,
course, locale, or migration rules. Prefer minimal new documentation.
