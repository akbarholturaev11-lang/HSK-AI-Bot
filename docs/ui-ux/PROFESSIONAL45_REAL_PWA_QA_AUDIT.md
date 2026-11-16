# HSK AI Professional45 — REAL learner PWA evidence matrix

**Authority:** [45 exact guidelines](https://github.com/akbarholturaev11-lang/HSK-AI-Design-System/tree/restore/hsk-ai-professional-unified-audit-20261115/docs/portable/guidelines), source SHA `09f95a3a62b1461de3aeb0f06f85864a62650216`. Implementation branch `feat/pwa-professional-45-design-real-source-20261116` (NOT main).

**Scope:** existing learner iPhone PWA HTML, mobile navigation and currently shipped workflows. Android native is NOT included in this branch. **Conditional** is not missing functionality: the component should not be invented where the existing product does not need it. This is a code/applicability audit; final device QA must still verify outcomes.

**Safety:** QA runs under dedicated Railway QA project only. No real DB/account, Telegram bot, R2, payment, AI secrets or production services. `app/qa_professional45_preview.py` serves original `app/static` files with safe clearly scoped synthetic QA API responses; NEVER use QA data to assert production behavior.

| # | Exact guideline file | Applicability | What the real PWA must do / evidence scope | Validation |
|---:|---|---|---|---|
| 1 | `design-foundations/borders-and-dividers.md` | Applicable | PWA course, practice, dictionary, checkout; borders, focus and selected/error distinctions | CSS + screenshot review |
| 2 | `design-foundations/colors-semantic.md` | Applicable | Preserve existing PWA semantic tokens; truthful success/pending, red Orb | Contrast review in actual themes |
| 3 | `design-foundations/colors.md` | Applicable | Light/dark contrast, non-color feedback | Both themes and screenshots |
| 4 | `design-foundations/data-visualization.md` | Applicable | XP, Streak, ranking values must be server-owned; unavailable ≠ zero | Actual profile/XP/Streak |
| 5 | `design-foundations/iconography.md` | Applicable | 44px hit targets; preserve canonical artwork; Phosphor on new UI | Existing icons not blanket-replaced |
| 6 | `design-foundations/illustration.md` | Applicable | Canonical source Panda, Longlong and Voice Orb; no new mascot | Current source assets |
| 7 | `design-foundations/layout.md` | Applicable | 5-tab PWA, learning flow, separate XP/Streak screens, profile hierarchy | 320/390/430 screenshot comparison |
| 8 | `design-foundations/motion.md` | Applicable | Lesson reveal, cards, loading, reduced-motion, Voice Orb exception | Reduced-motion E2E |
| 9 | `design-foundations/spacing.md` | Applicable | Consistent section/row/card rhythm | PWA scoped CSS tokens |
| 10 | `design-foundations/surfaces-and-elevations.md` | Applicable | List dividers instead of nested floating cards; real overlays | PWA professional CSS |
| 11 | `design-foundations/typography.md` | Applicable | Hanzi→pinyin→meaning, two-line optional disclosure, readable localization | Screens + skill updated |
| 12 | `design-components/active-filters.md` | Applicable | Dictionary search/level/saved additive filters | Real dictionary controls |
| 13 | `design-components/badges.md` | Applicable | XP, Streak and Pro state labels only when verified | Server map/checkout |
| 14 | `design-components/banners.md` | Conditional | Only for actionable error/state notices on a real screen; no new banner by default | Existing loading/error surfaces |
| 15 | `design-components/buttons.md` | Applicable | Single semantic action; minimum 44px; selected/disabled; focus | CSS plus E2E |
| 16 | `design-components/chart-container.md` | Conditional | Use only where a genuine chart exists; never invent missing XP history | Streak calendar partial/unknown state |
| 17 | `design-components/checkbox-group.md` | Conditional | Only where multiple real options/actions are supported | No fabricated bulk UX |
| 18 | `design-components/clear-filter.md` | Applicable | Optional dictionary filters reset without losing course version | Dictionary levels/saved/search |
| 19 | `design-components/data-tables.md` | Conditional | Ranking uses compact row layout, not a fabricated sortable desktop table | Real ranking rows |
| 20 | `design-components/date-filter.md` | Conditional | Only if verified time-period selection exists | No fabricated calendar data |
| 21 | `design-components/date-picker.md` | Conditional | Not required without a date input in current learner PWA | Avoid inventing date controls |
| 22 | `design-components/distribution-charts.md` | Conditional | No verified score distribution; don't create fiction | No new chart |
| 23 | `design-components/dropdown-select.md` | Applicable | Dictionary level/current course controls; accessible selection | PWA dictionary |
| 24 | `design-components/hsk-ai-characters.md` | Applicable | Only canonical character SVG and moods; Voice Orb separate | Existing character source |
| 25 | `design-components/inline-filter-button.md` | Applicable | Compact dictionary filters; no nonfunctional chips | Saved/level filters |
| 26 | `design-components/modals-selection.md` | Conditional | Only for real option changes, avoid fake goal selection | Goal save from server |
| 27 | `design-components/modals.md` | Applicable | Two-X checkout discount; focus/Back; compact centered offer | Existing inline Pro implementation |
| 28 | `design-components/popovers.md` | Conditional | Only existing context help; no invented tutorials | Existing UI states |
| 29 | `design-components/progress-charts.md` | Applicable | Real XP today/daily goal, Streak target; honest unknown periods | pwa-professional45-course.js |
| 30 | `design-components/progress-stepper.md` | Applicable | Existing onboarding steps, preserve progression/Back | Canonical onboarding |
| 31 | `design-components/radio-button.md` | Conditional | Only when real exclusive choices need it | No decorative radio controls |
| 32 | `design-components/search-field.md` | Applicable | Hanzi/pinyin/translation search, clear and keyboard states | Real dictionary and phrases |
| 33 | `design-components/summary-cards.md` | Applicable | Server verified XP, Streak, profile; missing value ≠ zero | XP/Streak and profile |
| 34 | `design-components/text-field.md` | Applicable | iPhone text ≥16px, IME and draft safety | PWA CSS and text entry |
| 35 | `design-components/toasts.md` | Applicable | Server success only, retry errors, no fake payment confirmation | Bookmarks and checkout |
| 36 | `design-components/toggle.md` | Conditional | Only existing persistent preference controls | Existing preferences API |
| 37 | `design-components/tooltips.md` | Conditional | No hover-only essential text in mobile UI | Actual PWA controls |
| 38 | `design-components/trend-charts.md` | Conditional | No complete historical XP dataset; never interpolate | XP honest history unavailable |
| 39 | `design-patterns/collecting-feedback.md` | Applicable with known gap | Preserve drafts/pending and don't claim success before server acceptance | Existing feedback route needs device testing |
| 40 | `design-patterns/component-composition-and-customization.md` | Applicable | Use actual original PWA, not reconstructed HTML; preserve business | Scoped 45 CSS + source JS |
| 41 | `design-patterns/data-reports.md` | Applicable | Streak dates source-based; unknown days distinct; profile accuracy | Real verified progress only |
| 42 | `design-patterns/filter-and-sort.md` | Applicable | Version-aware dictionary plus level, saved/search AND logic | hsk-lugat.html |
| 43 | `design-patterns/professional-reference-gallery.md` | Reference only | Historical pictures are not HSK AI product UI; no foreign assets | Excluded from implementation |
| 44 | `hsk-ai-product-ux-contract.md` | Applicable + approved-future items | UIUX-002/003/004/005/008/009/012 implemented or staged; UIUX-007 verified adaptive checks remain future | Real source and current QA evidence |
| 45 | `introduction.md` | Applicable | Professional-first; canonical product overrides; report unverified work honestly | This matrix and actual E2E |

## Product improvements versus actual shipped truth

| Item | Implementation in this branch | What cannot yet be claimed |
|---|---|---|
| UIUX-002 | Dedicated full-page XP and Streak using server values, authenticated goal preference | Month-wide history where backend has only recent days; no fabricated activity |
| UIUX-003 | Course-version dictionary, ☆/★ DB/bookmarks API, saved-only; local QA fixture | Real account retention until migrated and verified with signed-in device |
| UIUX-004 | Existing phrases now compact list, independent save and audio | Live voice/TTS guarantees without actual provider/device |
| UIUX-005 | One profile hierarchy; removed duplicate Streak achievement | 320/390/430 and real phone screenshots until CI/device checks complete |
| UIUX-007 | **NOT implemented** as real separate server-scored adaptive in-lesson reviews | Existing mistakes review awards XP: cannot rebrand as adaptive without new server contract |
| UIUX-008 | Source-bound optional in-lesson flashcard from a previously taught word; no XP/grade | It does not replace canonical lesson quiz or server-grade responses |
| UIUX-009 | Removed unnecessary icon backplates in relevant scoped screens | No blanket icon replacement, existing brand art remains |
| UIUX-012 | Server-gated compact 20% offer; offer X returns to checkout, second checkout X exits | Exact live financial eligibility and quote need separate protected payment tests |

## Release gates

- **CI:** Analytics integrity and Backend/PWA performance contract must both pass for the **same HEAD SHA**. Run source-backed QA E2E in Chromium + WebKit on 320, 390, 430 CSS px; inspect screenshots and console errors.
- **Loading:** usable known shell immediately; actual partial/ready/error/retry, stable placeholders with no old screenshot authority. Check no real lesson or paid state fabricated.
- **Behavior:** iPhone (Safari / installed PWA), Back, keyboard, focus, reduced motion, long UZ/RU/TJ translations, native PWA scroll restoration and no broken lesson/checkout/API behavior.
- **Account:** do not deploy the bookmark migration to production without backup and verification. Only the isolated QA fixture is allowed until then.
- **QA isolation:** verify project/environment/secret import guard; unknown API 503; production payment/invoices 503; public domains only in dedicated QA service.
- **Status:** don't claim "45/45 visual/device validated" until actual evidence above is available. Planned UIUX-007 is a separate future engineering feature, not a license to fabricate adaptive lessons.
