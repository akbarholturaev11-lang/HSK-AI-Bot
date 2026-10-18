# HSK AI Android — UI v2 rejasi

> This plan was last updated in the repository on 2026-09-20. The design
> direction and proposed migration waves remain planning context; its branch,
> current-status and next-task notes are historical. Check current code and
> `AGENTS.md` before treating any checklist or rollout item as today's state.

## Maqsad

Android ilovani funksional logikani o'zgartirmasdan professional, bir xil va
brendga xos ko'rinishga olib kelish.

UI v2 quyidagilarni hal qiladi:

- generic Material spinner va tasodifiy loading holatlarini HSK AI brend holatiga almashtirish;
- ekranlar bo'ylab takrorlangan oddiy `Surface`, `Button`, `OutlinedButton`
  kombinatsiyalarini bitta design system orqali boshqarish;
- asosiy kartalar, navigation, sheet va modal'larda yengil glass ko'rinish yaratish;
- primary action'larni glass ichida yo'qotib yubormasdan aniq hierarchy saqlash;
- light/dark mode, uz/ru/tg, direct/play flavour va mavjud Mini App rang
  kontraktini buzmaslik;
- yangi UI sabab cold start, scroll yoki interaction sezilarli sekinlashmasligi.

## Non-goals

Bu ish:

- backend contract'larini o'zgartirmaydi;
- course/progress/payment/subscription logikasini o'zgartirmaydi;
- navigation destination'larini qayta qurmaydi;
- Mini App'ni bir vaqtning o'zida redesign qilmaydi;
- birinchi bosqichda blur uchun uchinchi tomon runtime dependency qo'shmaydi.

## Vizual prinsiplar

### 1. Hierarchy

Hamma narsani glass qilish mumkin emas.

- **Primary CTA** — solid `Cinnabar`.
- **Status / warning / success** — semantik rangli surface.
- **Neutral card / chrome / secondary action** — glass surface.
- **Danger action** — alohida semantik rang; glass ichida yashirilmaydi.
- **Loading** — HSK AI tone-seal brendi; aylanuvchi generic spinner emas.

### 2. Glass

Birinchi versiya dependency'siz:

- translucent surface;
- 1 dp bright border;
- juda yengil vertical highlight;
- restrained shadow;
- dark mode'da Cosmos Blue raised surface.

Real background blur keyin alohida performance gate'dan o'tadi. Call-site API
shunday quriladiki, blur qo'shilganda ekran kodini qayta yozish talab qilinmasin.

### 3. Motion

Motion ma'no uchun ishlatiladi, bezak uchun emas.

- press scale: taxminan `0.985`;
- micro transition: 120–220 ms;
- sheet/dialog entrance: 220–320 ms;
- loader breathe: 1.0–1.5 s loop;
- infinite rotation yo'q;
- scroll paytida doimiy og'ir animation yo'q.

### 4. Radius / spacing

Boshlang'ich tokenlar:

- small control: 12 dp;
- button: 16 dp;
- card: 16–20 dp;
- major glass shell: 20–28 dp;
- minimum touch target: 48 dp;
- content horizontal spacing: mavjud 16 dp bazasi saqlanadi.

## Design system komponentlari

### Phase 1 — foundation

- [x] `HskBrandLoader`
- [x] `HskGlassSurface`
- [x] `HskPrimaryButton`
- [x] `HskGlassButton`
- [x] floating glass bottom navigation
- [x] generic spinner'larni asosiy ekranlarda branded loader'ga almashtirish
- [x] Profile ekranida glass pilot

### Phase 2 — loading va state system

Rejalashtirilgan komponentlar:

- [x] `HskSkeleton` API mavjud; 2026-10-15 source auditida hozircha ekran call-site’i topilmadi.
- [ ] `HskLoadingBlock`
- [ ] `HskEmptyState`
- [ ] `HskErrorState`
- [ ] `HskInlineLoader` kerak bo'lsa compact loader'dan ajratish

Qoidalar:

- app cold start / katta route boot -> brand loader;
- card list network refresh -> skeleton;
- button request -> compact brand loader;
- background refresh -> content saqlanadi, full-screen loader ko'rsatilmaydi.

### Phase 3 — interaction primitives

Yaratiladi / standartlashtiriladi:

- [ ] `HskIconButton`
- [ ] `HskActionRow`
- [ ] `HskSegmentedControl`
- [ ] `HskChip`
- [ ] `HskProgressBar`
- [ ] `HskBadge`
- [ ] press / disabled / loading holatlari

### Phase 4 — sheets, dialog va chrome

- [ ] `HskBottomSheet` visual wrapper
- [ ] `HskDialog`
- [ ] `HskTopBar`
- [ ] `HskSnackbar`
- [ ] overlay/dim tokenlari
- [ ] keyboard va safe-area tekshiruvi

## Ekranlarni ko'chirish tartibi

### Wave A — xavfi past

1. Profile
2. Dictionary
3. Rating

Maqsad: card, action row, loader va sheet primitives'ni real kontentda
mustahkamlash.

### Wave B — o'qish oqimi

4. Course
5. Practice
6. Mistakes

Bu yerda progress, node, exam va practice interaction'lar bor. Visual
o'zgarish business state'dan qat'iy ajratiladi.

### Wave C — interaction og'ir ekranlar

7. AI Voice
8. Lesson
9. Foundation
10. Onboarding

Mic/recording, audio, lesson completion va onboarding flow'lari sabab bu wave
oldingi primitives CI va real-device test'dan o'tgandan keyin qilinadi.

### Wave D — maxsus holatlar

11. Paywall / limit gate
12. Update card
13. Ads
14. Widget setup

Bu joylarda policy yoki monetization ta'siri bor; visual refactor alohida
regression tekshiruv bilan qilinadi.

## Loader qoidasi

HSK AI loader:

- launcher/tone-seal asset'idan foydalanadi;
- o'zi aylanmaydi;
- seal yengil breathe qiladi;
- orqasida soft cinnabar halo bor;
- compact va full variant mavjud;
- accessibility uchun indeterminate progress semantics beradi.

Keyingi iteratsiyada kerak bo'lsa panda animation alohida hero-loading holatiga
qo'shiladi. Oddiy API request uchun katta panda ko'rsatilmaydi.

## Performance gate

Har wave uchun:

- yangi katta runtime library qo'shishdan oldin zarurati isbotlanadi;
- list item ichida blur/graphics effect ko'paytirilmaydi;
- infinite animation soni minimal;
- release build'da R8 bilan tekshiriladi;
- oldingi cached-first course startup saqlanadi.

Real blur faqat:

1. API compatibility tekshirilgandan;
2. APK size ta'siri o'lchangandan;
3. scroll jank yo'qligi real device/emulator'da tasdiqlangandan keyin qo'shiladi.

## Accessibility gate

- touch target >= 48 dp;
- dynamic font scale'da CTA kesilmasligi;
- progress semantics saqlanishi;
- rangning o'zi statusning yagona signali bo'lmasligi;
- light/dark kontrast;
- uz/ru/tg uzun matnlarda overflow tekshiruvi.

## Validation gate

For an Android change, use `android/README.md` and the active Android workflow
as the exact source for checks. As of this plan audit, CI runs nine project
checkers, unit tests and lint for both flavours, emulator flow regressions,
debug assembly and release-bundle validation. Keep the visual QA below for a
large UI wave; a passing build does not prove the visual/accessibility review.

## Visual QA

Har katta wave tugagach kamida:

- light mode;
- dark mode;
- 360–390 dp telefon kengligi;
- katta font scale;
- uz / ru / tg;
- loading / error / empty / success;
- direct va play build

ko'rib chiqiladi.

## Historical branch / rollout snapshot — 2026-09-20

These bullets record the task's intended workflow on that date; they are not a
current branch or promotion rule. Use `AGENTS.md` for the repository policy.
The old push-vs-PR/promotion wording is part of the unresolved policy review in
`docs/DOCUMENTATION_AUDIT_2026-10-14.md` (D08).

Task snapshot:

- development: `codex/cloud-ai`;
- `main` to'g'ridan-to'g'ri UI commit olmaydi;
- draft PR CI uchun ochiladi;
- UI green + review bo'lmaguncha release qilinmaydi.

Android UI kodi production foydalanuvchiga faqat yangi APK release qilingandan
keyin yetib boradi.

## Current source status — 2026-10-15 audit

- `HskGlassSurface`, `HskPrimaryButton`, `HskGlassButton`, the branded loader
  and floating glass navigation exist in source.
- Glass/primary-button call-sites span several feature screens, so the old
  "Profile pilot first" sequence is no longer a reliable current backlog.
- `HskSkeleton` has an implementation but no screen call-site in this
  checkout. The other proposed loading, empty/error and interaction primitives
  remain partial or absent; check their source before taking a checklist item.
- No device screenshot, accessibility review, Play/Direct release, or live
  rollout is established by this source audit. This section describes the
  checkout only.
