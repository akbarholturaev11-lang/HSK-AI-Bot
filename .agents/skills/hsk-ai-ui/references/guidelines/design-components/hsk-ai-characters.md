> **HSK AI professional design guideline — portable review copy.** Source: `__docs__/design-components/hsk-ai-characters.mdx`, Git blob `aff314974d07aeae8ab04a26161a8c4e09c8e500`. 0 historic figure references and 0 MDX demo blocks; source images / vendor runtime code were not copied. Source prose remains an internal derivative draft pending rights and detailed visual parity review; this does not assert a live app feature.

# HSK AI characters

> **Canonical HSK AI guidance:** Use only the actual HSK AI Panda, approved supporting characters and the separate approved Voice Orb. Character roles must be verified against the current app renderer. This is the sole character-design policy page for HSK AI.

HSK AI already has a multi-character learning system and a separate AI Voice Orb. A new illustration must match the established appearance, pedagogical role and reaction grammar rather than introducing an arbitrary mascot.

## Canonical character roles

The existing PWA source `app/static/assets/characters/hsk-character-pack.js` defines:

| Character | Source label | Existing source role | Usage guard |
| --- | --- | --- | --- |
| Panda | `熊猫` | `main_coach` | Existing primary learning companion; preserve face, ears, silhouette and recognized canonical poses. |
| Longlong (Dragon) | `龙龙` | `energy_milestone` | Do not invent new rewards or achievement eligibility; use the actual lesson state. |
| Hehe (Crane) | `鹤鹤` | `grammar_precision` | Teaching/grammar-focused contexts where actually selected by the learning UI. |
| Wuwu (Monkey) | `悟悟` | `drill_dialogue` | Existing drill and dialogue learning contexts. |
| Yueyue (Rabbit) | `月月` | `memory_warning` | Existing memory and review contexts. |

These are grounded in current code; not every character must appear on every screen. The native Android `LessonCharacters.kt` routes certain lesson card types to Crane, Monkey, Rabbit or Panda; do not replace these choices using an unrelated source mascot guideline.

## Approved moods and teaching responses

The PWA character pack currently defines `idle`, `talk`, `correct`, `wrong`, `celebrate`, `proud`, `dismissive`, `one-heart`, and `loading` moods. Use a current, supported reaction for its actual meaning. Do not substitute generic celebratory artwork for an incorrect answer or present a correct reaction when scoring has not been confirmed.

- Preserve the existing **correct and incorrect** lesson reactions, expression details and supported motion; both sides of feedback matter.
- Preserve the motion system's reduced-motion handling. Text, icon and learning-state feedback must remain understandable if animation is disabled.
- Keep the same visible identity and proportions across iPhone PWA and Android. Native port and PWA renderer may differ technically; parity must be checked using real screenshots before claiming 1:1 appearance.
- Do not move characters over an answer target, keyboard, essential Hanzi/pinyin text, payment controls, or the AI Voice Orb's active interaction.

## Character identity and learning guidance

Character identities and reactions must arise from actual HSK AI learning states and approved assets. Do not invent other characters, reward economies, accessory stores, school workflows or unimplemented assessment roles.

| Design principle | HSK AI application |
| --- | --- |
| A guide responds to a meaningful user action | Use an approved Panda or other actually routed character and its existing learning-state reactions. |
| High-stakes testing should avoid answer-giving help | Respect the current HSK AI exercise rules and reveal states; no invented separate assessment-proctor character. |
| A character should not hide crucial instructions | Preserve the readable question, choices, accessibility status and screen layout first. |
| System errors need clear, neutral explanations | Use HSK AI error messages and recovery controls rather than a mascot as the sole indication. |
| Character expressions should be purposeful | React to real user and learning states; avoid arbitrary endless animation or gimmicky recoloring. |

## AI Voice Orb is a separate interactive visual

The actual AI Voice Orb is a distinct pearl-like cinnabar/red visual with an established renderer and supported listening/speaking motion. Preserve its approved interaction and appearance; do not flatten it into a generic school illustration, recolor it to match another brand, or confuse its voice-processing state with a correct/incorrect lesson reaction.

The current native renderer is `android/app/src/main/java/com/pomp/hskai/feature/voice/VoiceV8Orb.kt`. Consult the **actual current** PWA voice implementation and approved prototype before introducing any cross-platform Orb change. This page does not authorize production modifications.

## Artwork sourcing and acceptance

1. **Obtain actual canonical imagery** from current HSK AI source/project assets. Never substitute a generic cartoon, random stock Panda or approximate AI-generated lookalike.
2. **Use matching approved variants.** Do not remove an existing pose or incorrect-answer reaction just because a source screenshot depicts a different character.
3. **Ground all product artwork in the HSK AI app.** A generic diagram can explain spacing or accessibility, but cannot replace an approved HSK AI screenshot, asset or renderer.
4. **Label UI accurately.** Do not invent classroom management, rewards, character customization or other features unsupported by HSK AI code.
5. **Verify in real mobile layouts.** Compare iPhone PWA and Android in default and enlarged text, light/dark mode, interactive answers, motion-reduced mode, and voice keyboard overlays.
6. **Avoid inventing new image prerequisites.** If a canonical HSK AI asset is not accessible, identify the missing source instead of generating an approximate brand replacement.

## Documentation scope

This document is grounded in existing HSK AI source structure; it introduces no new asset, font, commercial tier, gameplay reward, screen, video or live character functionality. Updating the production Panda, side characters or Orb is out of scope for adapting the design-system documentation.
