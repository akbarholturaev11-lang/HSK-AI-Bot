---
name: hsk-ai-ui
description: Use this skill when designing or reviewing HSK AI Telegram Mini App UI, course screens, quiz screens, homework flow, voice roleplay, subscription screens, and mobile UX.
---

# HSK AI UI Skill

You are improving the HSK AI Telegram Mini App interface.

Rules:
- Do not break existing lesson logic.
- Do not break quiz logic.
- Do not break homework logic.
- Do not break Telegram WebApp SDK.
- Improve only UI/UX unless explicitly asked to change logic.
- Mobile-first.
- Premium, clean, not childish.
- Chinese text must show characters, pinyin, and translation.
- One main action per screen.
- Course is the core product.

When reviewing UI, check:
1. visual hierarchy
2. button clarity
3. spacing
4. mobile readability
5. Telegram safe area
6. progress feeling
7. reward feeling
8. quiz dopamine
9. subscription conversion
10. whether the screen helps learning

Before editing code:
1. explain the weak points
2. propose exact changes
3. list files to edit
4. estimate risk level
5. then make small safe patches only

## One-Line Expandable Text — UI/UX standard

Apply this presentation to **non-essential helper text, secondary descriptions, and explanatory hints** in HSK AI learner PWA and Android. Match the established Admin PWA interaction in `app/static/admin-pwa/app.js` (`foldHints`, `toggleHint`) and `app/static/admin-pwa/styles.css` (`.hint-clamp`, `.hint-fold`) visually; implement with the appropriate native controls for each platform rather than importing Admin PWA code.

1. **Collapsed by default:** show at most **one rendered text line**, with an ellipsis (`…`) when the text overflows.
2. **Conditional indicator:** only when the text actually overflows, show a small, unobtrusive **chevron-down** (`⌄`) at the right edge. If the full text fits on one line, show no chevron and do not present an expand control.
3. **In-place expand:** tapping either the truncated text or the chevron reveals the **entire text in the same location**; the indicator becomes **chevron-up** (`⌃`). Tapping again collapses it to one line. Never navigate to a new screen or open a modal for this.
4. **Minimal presentation:** no `Подробнее` / `Свернуть` labels, additional buttons, decorative cards, icon backplates, borders, shadows, or extra background surfaces. The text and chevron form one accessible interaction target.
5. **Motion:** use a subtle 150–250 ms expansion/collapse transition without abrupt jumps or blocking the interface. Respect the system's reduced-motion preference.
6. **Accessibility:** make the interaction keyboard/screen-reader operable, expose its expanded/collapsed state, and preserve a usable touch target (**at least 44 CSS px on PWA / 48 dp on Android**) without making the visual chevron oversized.
7. **Do not truncate essential content:** lesson explanations required to answer, question/answer text, instructions, critical feedback, payment prices/terms, limits, error recovery, or important safety notices must remain fully understandable without expanding a hint. Apply this pattern only where optional detail can safely be hidden.

**Review check:** test short vs overflowing text, very narrow screens, long UZ/RU/TJ translations, large text settings, expanded/collapsed state, and reduced motion. Avoid applying a one-line clamp indiscriminately to all text elements.
