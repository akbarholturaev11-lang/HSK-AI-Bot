## Communication

Repository-wide language and script policy is in `AGENTS.md`, under
"Loyiha va aloqa". Do not impose a separate Uzbek Latin-only requirement here.

## Mandatory Project Guidance First

Before making any code change, always read the project guidance files first and follow their rules.

Read these existing root files before code changes:
- `AGENTS.md`
- `AI_RULES.md`
- `PROJECT_MEMORY.md`

Read `CLAUDE.md` as Claude-specific guidance, plus the README and other docs
relevant to the task. The repository's `AGENTS.md` defines the shared session
startup and memory rules.

When the work touches the Android app, read these first:
- ANDROID_CONTEXT.md — current state, open bugs, where things live
- ANDROID_RELEASE_CHECKLIST.md — how a release is cut
- android/README.md — flavours, signing, in-app updates

Do not start editing code until these guidance files are checked.

When working on a specific feature, first identify and read the related existing files, services, handlers, models, migrations, tests, and frontend files.

Do not guess the architecture. Follow the existing project structure and rules.

## Language and Mini App Change Rules

When adding or changing user-facing text, identify the languages supported by
that surface and keep the text in sync across them. For surfaces supporting
all three project languages, those are:

- Russian
- Tajik
- Uzbek

Do not add new visible text in only a subset of a surface's supported languages
unless the user explicitly approves it.

Before changing Mini App UI, apply the risk-based audit in `AGENTS.md`.
For navigation, lesson flow, paywall, authentication, or a substantial UX redesign,
report impact, proposed patch, files and risk. For a small visual/copy-only fix
use a focused source check and relevant screen smoke test instead of a full audit.
An explicitly requested in-scope change needs no second approval; clarify only
materially unresolved behavior, business policy or scope.

Avoid awkward UI, unnecessary animation, random badges, confusing buttons, and
decoration without a clear user benefit.

Mini App changes must be:
- clean
- simple
- modern
- useful
- consistent with existing design

If uncertainty would materially change behavior, content, or scope and cannot
be resolved from the request or existing code, ask. Otherwise proceed using the
best-supported interpretation.
