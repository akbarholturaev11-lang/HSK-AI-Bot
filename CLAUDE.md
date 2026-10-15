## Communication Rule (STRICT)

Always communicate with the user ONLY in Uzbek. This is a strict, non-negotiable rule.
All explanations, questions, summaries, and status updates must be written in Uzbek.
(Code, file paths, and technical identifiers stay as-is — only the conversation language is Uzbek.)

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

Before editing Mini App UI, follow the UI audit steps in `AGENTS.md`: report the
weak points, user impact, exact proposed changes, files, and risk. After that
audit, proceed within the requested scope; do not ask for approval again when
the user has already requested that UI change. Ask only when an unresolved
choice would change product behavior, learning flow, business rules, or expand
the requested scope. The audit applies especially to changes affecting:

- layout
- navigation
- buttons
- colors
- lesson flow
- paywall
- profile
- AI Voice UI
- any visible user experience

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
