## Communication Rule (STRICT)

Always communicate with the user ONLY in Uzbek. This is a strict, non-negotiable rule.
All explanations, questions, summaries, and status updates must be written in Uzbek.
(Code, file paths, and technical identifiers stay as-is — only the conversation language is Uzbek.)

## Mandatory Project Guidance First

Before making any code change, always read the project guidance files first and follow their rules.

Required first-read files:
- PROJECT_MEMORY.md
- CLAUDE.md
- README.md if present
- relevant docs or rules files inside the project

Do not start editing code until these guidance files are checked.

When working on a specific feature, first identify and read the related existing files, services, handlers, models, migrations, tests, and frontend files.

Do not guess the architecture. Follow the existing project structure and rules.

## Language and Mini App Change Rules

When adding or changing any user-facing text, first check whether it needs all 3 supported languages:

- Russian
- Tajik
- Uzbek

Do not add new visible text in only one language unless the user explicitly approves it.

Before changing Mini App interface, ask the user first if the change affects:

- layout
- navigation
- buttons
- colors
- lesson flow
- paywall
- profile
- AI Voice UI
- any visible user experience

Do not add cringe UI, unnecessary animations, random badges, confusing buttons, or decorative elements without approval.

Mini App changes must be:
- clean
- simple
- modern
- useful
- consistent with existing design

If unsure, stop and ask before editing.
