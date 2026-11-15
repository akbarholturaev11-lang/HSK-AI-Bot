# HSK AI PWA — 45-rule design review, strictly one section at a time

## Authority and immutable baseline
- **Exact source snapshot:** \`main\` commit \`a6689aafbd10c8880907d8f0f5a5c342516be6c0\` (2026-11-16).
- **Preserved whole-repository copy:** \`snapshot/pwa-1to1-20261116\`, created at that exact commit and **never modify this snapshot branch**.
- **Working review branch:** \`feat/pwa-45-guidelines-review-20261116\`, created from the same exact source commit.
- **1:1 verification type:** branch commit identity and complete recursive tree SHA/contents, 9,876 tracked blobs and 10,295 tree entries (\`truncated=false\`); \`app/static/course-v3.html\`, its CSS token file and all other committed backend/static files are identical before review-only additions. **This is source parity, not authenticated runtime/pixel/device parity.** Test iPhone WebKit/installed PWA separately before claiming visual 1:1.
- **Design authority:** [professional 44 plus HSK AI UX page 45](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/blob/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/README.md), checked at design-system head \`09f95a3a62b1461de3aeb0f06f85864a62650216\`. Also read current main \`AGENTS.md\`, \`AI_RULES.md\`, \`.agents/skills/hsk-ai-ui/SKILL.md\`, \`HSK_AI_UI_UX_IMPROVEMENTS.md\` and \`docs/PERFORMANCE_BACKEND_PWA_GOALS_REQUIREMENTS.md\`. Re-check newest source revisions before later integration.

## One HTML preview, progressively filled
- **Standalone UI-only HTML:** [pwa-45-course-preview.html](pwa-45-course-preview.html). Inline official brand SVG, official original \`HSKCharacters\` renderer and original \`design-tokens.css\` theme token values.
- Its example progress numbers / course content are **DEMO**, not the user's actual XP, rank, purchases, access or lesson results.
- The initial file contains the interactive **Course** section only. The other four tab names intentionally remain visible but unimplemented in the preview until their **separate** reviews. Do not invent or silently publish their behavior.
- The **original 1:1 PWA source** remains in the full snapshot and initial working branch. The standalone preview is a deliberately **redesigned demo, not an exact clone of a running authenticated page**. It performs no real login, payment, grading, writes or API calls.
- Never add the design-lab file to production PWA routing/navigation or deploy it as a public app screen on this task.

## Sequence — one distinct section at a time
| Stage | Main surface | Required detailed review | Current status |
| --- | --- | --- | --- |
| 0 | Full 1:1 source and dependency inventory | Exact snapshot branch, Git tree equality and original static file inventory | **SOURCE PASS**, authenticated visual/device parity **UNVERIFIED** |
| 1 | **Course** | Level/version header, streak/XP summary, progress geometry, learning path, canonical mascot, in-lesson entry, responsive structure, loading/partial/error, keyboard/accessibility | **COURSE PREVIEW WRITTEN**, browser/device visual validation **NOT RUN** |
| 2 | Practice | Dictionary, ready phrases, character recognition, pronunciation, test centre, My Mistakes; each existing subview individually, without breaking account state | **NOT STARTED** |
| 3 | AI Voice | Existing red pearlescent orb, actual Listening/Thinking/Speaking states, keyboard/composer and permissions, safe areas | **NOT STARTED** |
| 4 | Rating/Friends | League podium, genuine score row anatomy, empty/loading/partial/error and social controls | **NOT STARTED** |
| 5 | Profile/Settings | Accurate verified profile data, streak/XP, status/Pro, notifications, settings, 20% checkout UX per approved owner plan | **NOT STARTED** |
| 6 | Auxiliary screens | Li onboarding, account/login, dedicated lesson exercises, subscription/payment route, result overlays, vocabulary detail and other embedded flows — **each separately** | **NOT STARTED** |

**Rules for each future stage:**
1. Read the corresponding original product PWA HTML/CSS/JS and 45-rule topic pages; preserve canonical source art and learning/paywall/analytics boundaries.
2. Build the next isolated UI-only visual/interaction preview **in the same standalone HTML document**, keeping previous reviewed sections available.
3. Compare to the exact source snapshot and document the proposed hierarchy, controls, states, behavior and justified visual differences; never claim the preview was pixel-identical baseline or already shipped.
4. Do not modify the original course backend, runtime PWA, security, database, subscriptions, payment or navigation. A separate user-approved implementation task and actual browser/device/regression testing are required to integrate the reviewed design into production.
5. Report code-level validation distinctly from browser screenshot comparison, real Safari/iPhone evidence and backend acceptance.

**Current result:** baseline source copy verified, no original PWA files changed, first Course preview created for visual review only. Subsequent sections must be handled one at a time.
