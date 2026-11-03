# Widget reference atlas

Execution evidence belongs to `SMART_REMINDER_MASTER_PLAN.md` §17.83. The final
asset is `android/app/src/main/res/drawable-nodpi/widget_panda_duo_sheet.png`:
36 original panda poses in a 6×6, 1254×1254 RGBA atlas. `WidgetPandaArt` holds
measured body frames and renders a common transparent viewport: close-up standing heads fill the lower
card, while full-body return, tiny and flattened poses retain their intended scale. Earlier approved assets
remain available for recovery.

The identity comes from the approved broad-headed HSK AI panda. The mood,
upper counter/flame/short-caption and color reference is the official
[Duolingo widget article](https://blog.duolingo.com/widget-feature/) and its
linked 25-illustration sheet. Its exact time/inactivity thresholds and proprietary
font are not asserted; the implementation uses the existing bundled rounded
Nunito font and current authenticated HSK AI personal context. Captions are local
canonical UZ/RU/TJ resources, never baked into the image.

Rows are early/beginner/growing/veteran (0–5), waiting (6–11), dramatic waiting
(12–17), late moods (18–23), playful zero-streak return invitations (24–29), and
completion/milestones (30–35). Generic invitation text and known positive-time
age never establish complete inactivity or a failed reminder. Operational
unknown/stale/quiet states stay calm. Atlas art never grants consent or sends.

The actual personal-minute→day-end interval advances unsecured nonzero-streak
moods at .33/.66/.85. Known positive-history age with a zero streak selects
7/30/90 calendar-day return bands; unknown history stays calm. These are HSK AI
visual choices, not published Duolingo algorithm values. The native common
viewport is 256×160; measured frames retain each pose's intended crop/scale.
The install-help hero reuses a full-body approved original panda rather than
the older glossy promotional illustration. No raster postprocessing is used.

Generated with the built-in image-generation tool. The prior twelve-pose image
was an interim preview and is not shipped. The final generation prompt follows.

## Prompt

Production asset, stylized-concept / identity-preserving illustration. Make ONE high-resolution square RGBA sprite atlas, EXACTLY SIX EQUAL COLUMNS by SIX EQUAL ROWS, 36 ORIGINAL PANDA illustrations in row-major order. Input 1 is the approved HSK AI panda IDENTITY reference: keep its broad softly squared white head, bold asymmetrical black eye patches, large expressive eyes, black ears and compact body, coral paw pads. Input 2 is a Duolingo widget MOOD/COMPOSITION reference only: reproduce the range of playful moods and visual storytelling using this panda, never the owl, no Duolingo logos, no copied text. Modern crisp flat vector-like solid shapes, NO gloss, NO airbrush, NO fur, NO photorealism, NO heavy shading, NO outlines. IMPORTANT: perfectly transparent empty background with alpha ZERO. NO cast shadows, NO glow/halo, NO white or colored fringe, NO grain/noise, NO checkerboard, NO frames, NO backgrounds baked into any cell. Each full compact panda or purposeful cartoon pose is centered entirely within its equal square cell, with 12% empty transparent margin from EVERY cell edge; no overlap or pieces in adjacent cells. The app draws the caption/count/flame separately above the art. NO TEXT OR NUMBERS ANYWHERE. Exact row-major cells: Row 1: (0) hopeful beginner holding a tiny bamboo sprout; (1) growing learner with a plain green book; (2) confident veteran with green bamboo-leaf headband; (3) curious beginner peeking up with big eyes and sprout; (4) relaxed growing learner leaning on a closed green book; (5) athletic veteran stretching with the leaf headband. Row 2: (6) patient friendly wave; (7) half-lidded playful impatient pout; (8) gently pleading large shiny eyes; (9) paws clasped asking sweetly; (10) paws on cheeks concerned expression; (11) crossed paws and one raised eyebrow. Row 3: (12) comic calm portrait pose hands folded like a museum painting, no canvas; (13) dramatic opera-singing pose eyes closed mouth open; (14) lying on belly looking up; (15) squash-and-stretch flattened wide panda with eyes visible; (16) slumped seated panda with sad small smile; (17) comically worried panda with one small sweat droplet. Row 4: (18) stern funny crossed paws, no hostility; (19) cartoon crying melodramatically with huge eyes, friendly not tragic; (20) exaggerated startled upright panda with spiky orange accent shapes contained behind it, no real fire; (21) determined angry eyebrows leaning forward; (22) funny cartoon villain face with reddish eyes, no scary violence; (23) exaggerated grumpy round panda with puffed cheeks. Row 5, time-away fantasy moods: (24) sleepy cuddly panda curled up with tiny star accents; (25) very small lonely panda looking up, no spotlight or background; (26) stylized translucent icy-blue frozen panda sitting inside a simple small ice shape; (27) friendly cute stylized panda skeleton costume with clearly panda skull/ears, no gore, seated quietly; (28) big pleading panda offering a few small bright flowers; (29) welcoming panda waving both paws with joyful recognition. Row 6, completion: (30) both paws raised in joy; (31) celebratory small fist pump; (32) beginner high-five while holding bamboo sprout; (33) growing learner hugging green book happily; (34) proud veteran leaf-headband panda smiling serenely; (35) milestone celebration veteran with raised paws and a few tiny colored confetti shapes inside its cell. Exactly 36 distinct cells. Keep the same appealing modern panda character throughout. 3072 by 3072 or similarly high-resolution SQUARE atlas preferred. Borders between cells must be generously empty and fully transparent, with absolutely no shadows or faint residual pixels.
