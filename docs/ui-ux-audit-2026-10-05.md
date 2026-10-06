# HSK AI — UI/UX va design-system auditi

2026-10-04–05 · Android + Telegram Mini App · Senior product design / implementation audit

**Tekshirilgan versiya:** main manbasidan sinxronlangan codex/local-ai, b35cb774bd5eca54f8d5df665dee136fb5d195cb. Ish worktree’i: /Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot. HEAD va origin/main teng. codex/local-ai 62 commit fast-forward qilindi. UI kodi tahrirlanmadi; commit/push qilinmadi.

**Implementation follow-up (2026-10-06):** Subscription’dagi country va payment method tanlovlari Mini’da bitta grouped surface va divider qatorlariga; Android direct host’da region, method va display-currency variantlari `ChoiceGroup`/divider qatorlariga o‘tkazildi. Row minimumi 66px/dp, selected radio holati va mavjud callback’lar saqlandi. Mini preview 390×844 va 320×700’da tekshirildi: horizontal overflow, console error yoki 44px’dan kichik visible target yo‘q; country/method tanlovi preview state’lari tasdiqlandi. Android `:app:compileDirectDebugKotlin` va `:app:installDirectDebug` BUILD SUCCESSFUL. Pixel 8 AVD'da ochilgan direct-debug app auth/LinkScreen'da to‘xtadi; checkout'ni account bilan tekshirish imkoni bo‘lmadi. Login qilinmadi, payment submit qilinmadi; commit/push yo‘q. User yuborgan Android Studio screenshot’ida onboarding intro [ko‘rindi][shot-onboarding-user]; bu tasvir hozirgi worktree revision’i ekanini mustaqil tasdiqlamadim.

**1. Umumiy xulosa**

HSK AI’da o‘z dizayn tilining yaxshi asosi bor: iliq qog‘oz ranglari, cinnabar qizil, xitoycha serif matn, kurs ketma-ketligi va Panda suhbatdosh/ustoz. Android light palette va Mini App Course palette aynan mos keladi. Shu asosni saqlash kerak.

“AI template” hissining asosiy sababi — oddiy ma’lumotning ham card, border, shadow va kichik badge’ga aylanishi; o‘qish mazmuni, navigatsiya va reklamaning bir xil kuchli bezak olishi. Radius, spacing va matn rollari markaziy tizimdan ko‘ra screen ichidagi lokal qiymatlar bilan boshqariladi. Panda ba’zan ustoz, ba’zan harakatlanuvchi dekor, ba’zan natijani kechiktiradigan cinematic elementga aylanadi.

Eng katta qayta ko‘rib chiqish kerak bo‘lgan joylar: Profile hierarchy, Mini App Practice limit, yangi so‘zning reading layout’i, completion/result va checkout presentation. Onboarding hamda Android Limit’ni to‘liq qayta qurish zarurati aniqlanmadi.

Bu auditda **tasdiqlangan P0 topilmadi**. P1 — kuchli hierarchy/usability/identity muammosi; P2 — consistency va o‘qish qulayligi; P3 — polish. Runtime’da ochilmagan holat uchun “vizual bug tasdiqlandi” deyilmagan.

**2. Tekshiruv qamrovi va real ekran dalillari**

Android Studio’da joriy main build/run qilindi. Studio install muvaffaqiyatini ko‘rsatdi; emulatorda com.pomp.hskai.debug / MainActivity ishlayotgani tekshirildi.

| Ekran | Real UI | Dalil / cheklov |
|---|---|---|
| Course/Home | Qisman: HSK 3.0 access dialog va ortidagi ekran | [Screenshot][shot-course]. Emulatordagi hisob faol HSK3 track uchun locked holatda |
| Practice | Ochiq holati ko‘rilmadi | [MainActivity:891][a-gate] Practice’ni HSK3 gate’ga qaytaradi |
| Lesson | Ko‘rilmadi | Shu access holati; to‘lov yoki track almashtirish bajarilmadi |
| Voice | Ko‘rildi | [Screenshot][shot-voice]; suhbat boshlanmadi |
| Dictionary | Ko‘rilmadi | Mavjud kirish Practice callback orqali; dictionary deep link yo‘q |
| Profile | Ko‘rildi | [Screenshot][shot-profile]; screenshotdagi yuklanayotgan ism/avatar alohida dizayn bug sifatida baholanmadi |
| Onboarding | User yuborgan [Android Studio screenshot][shot-onboarding-user] intro screen’ni ko‘rsatadi; current worktree build’i bilan bog‘liqligi tasdiqlanmagan | Visualda Panda ustoz, greeting bubble, localized copy va bitta “Boshlash” CTA; interaction/font-scale ko‘rilmadi |
| Limit | Ko‘rilmadi | Course access dialogidan alohida limit holati; koddan o‘rganildi |
| Subscription | Ko‘rildi | [Screenshot][shot-sub]; currency chooser ochilgan. Tarif/valyuta/to‘lov tasdiqlanmadi |
| Completion/result | Ko‘rilmadi | O‘qish natijasi yoki account progress yaratilmagan |

Tegishli Android screen’larda tayyor Studio @Preview yoki debug screen route topilmadi. Qolgan ekranlar kod auditi bilan qamrab olindi.

Mini App uchun 390×844 va 320×700 viewport’da source fayllar lokal HTTP serverdan responsive browser preview qilindi. Course’da Telegram init bo‘lmagani uchun auth gate ko‘rindi; Course/Home [screenshot][shot-mini-course]. Standalone Dictionary list [screenshot][shot-mini-dict], detail [screenshot][shot-mini-detail], stroke-order dialog [screenshot][shot-mini-stroke], Onboarding [screenshot][shot-mini-onboard] va Subscription preview currency chooser [screenshot][shot-mini-sub] render bo‘ldi. Mobile smoke’da ochilgan 4 sahifada document width viewport’dan oshmadi, JavaScript page error chiqmadi, visible button/link/input hit box’lar 44×44px minimumga yetdi. Dastlab 41px baland Course bot-return CTA, 38–43px Dictionary til/daraja controls topilib, CSS’da tuzatildi va qayta o‘lchandi. Dictionary detail’dagi izoh kartalari nested surface’dan divider-based reading sections’ga o‘tkazildi; stroke-order dialog `aria-modal`, background `inert`, Escape close va focus return bilan tekshirildi. Bular signed Telegram WebView/API session emas: Practice, Lesson, Voice, Profile, Limit, haqiqiy quote/to‘lov va completion flow’lari preview’da ochilmadi. Auth holati soxtalashtirilmadi. Yangi Mini screenshot’lar patch qilingan worktree’ni ko‘rsatadi; auditdagi kod/token inventari esa yuqorida ko‘rsatilgan b35cb774 baseline’dan olingan.

| Mini App screen | Browser preview | Chegara |
|---|---|---|
| Course/Home | Telegram init bo‘lmagan auth gate ko‘rildi | Course kontenti auth ortida |
| Practice | Ochilmadi | Shell auth gate; account kerak |
| Lesson | Ochilmadi | Lesson deep-link/session kerak |
| Voice | Ochilmadi | Auth/session va voice API kerak |
| Dictionary | Ko‘rildi: bundled data bilan search/filter/list | API sinxronligi tekshirilmadi |
| Profile | Ochilmadi | Authenticated shell kerak |
| Onboarding | Ko‘rildi: welcome state | Keyingi savollar/API submit tekshirilmadi |
| Limit | Ochilmadi | Entitlement state talab qiladi |
| Subscription | Ko‘rildi: preview currency chooser | Haqiqiy narx quote, checkout va submit tekshirilmadi |
| Completion/result | Ochilmadi | Real lesson/practice natijasi talab qiladi |

**3. Android design-system implementation auditi**

[Color.kt][a-colors], [Type.kt][a-type], [Theme.kt][a-theme], [HskSurfaces.kt][a-surface] va [HskButtons.kt][a-buttons] haqiqiy design-system bazasini beradi. PompColors uchun 1 418 reference bor. “Screen’lar design system’dan umuman foydalanmaydi” degan xulosa noto‘g‘ri. Muammo — colors va bir nechta komponent ishlatiladi, lekin shape, spacing, type va surface rollari yetarli boshqarilmaydi.

Quyidagi hisob 177 ta main Kotlin fayliga tegishli. Comment’lar chiqarilgan; direct checkout alohida ko‘rildi.

| O‘lchov | Natija | Talqin |
|---|---:|---|
| Barcha RoundedCornerShape call’lar | 254 | Named/asimmetrik corner’lar ham bor |
| Ularning literal dp argumentlari | 279 / 26 turli son | Har biri mustaqil radius token degani emas |
| .padding literal argumentlari | 748 / 35 qiymat | Icon size/offset bu hisobga qo‘shilmagan |
| PaddingValues literal argumentlari | 64 / 11 qiymat | Main Kotlin |
| spacedBy literal argumentlari | 118 / 15 qiymat | Main Kotlin |
| fontSize literal assignment | 242 / 36 qiymat | Hanzi va dekorativ glyph o‘lchamlari ham bor |
| lineHeight literal assignment | 85 / 31 qiymat | Mahalliy type scale’lar mavjud |
| letterSpacing literal assignment | 15 / 8 qiymat | Mahalliy override’lar |
| Hex Color literal | 237 / 161 rang | Markaziy palette ham qo‘shilgan |
| core/design tashqarisidagi hex Color | 68 / 55 rang | Illustration ranglari ham bo‘lishi mumkin |
| To‘g‘ridan-to‘g‘ri Surface call | 203 | Bu son HskGlassSurface substring’ini qo‘shmaydi |
| HskGlassSurface call | 50 | Shared component definition ham kiritilgan |

**Barcha main Kotlin radius sonlari, dp:** 0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 24, 26, 28, 30, 34, 999.

**Padding-only qiymatlar, dp:** 0, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 45, 60, 64.

0 — square corner, 999 — pill, ayrim kichik qiymatlar esa badge/illustration geometriyasi. Muammo ularning mavjudligida emas; bir xil content row va CTA rollarida 11/12/13/14/15/16 kabi yaqin qiymatlar tokensiz tanlanishida.

**[P1] Surface default’i bezakni avtomatik tarqatadi.** HskGlassSurface default 20dp radius va 12dp shadow beradi; light holatda 72% oq fill, oq border va ichki gradient wash ishlatadi. Practice va Dictionary kabi ma’lumot satrlarida har item ko‘tarilgan obyektga aylanadi. Android’da bu komponent haqiqiy background blur ishlatmaydi; keng tarqalgan blur mavjud deb xulosa qilinmadi.

**[P2] Typography coverage to‘liq emas.** PompTypography faqat yetti Material rolini belgilaydi. labelSmall, labelMedium, titleSmall va headlineSmall kabi ishlatiladigan rollar Material default bilan qoladi. Hanzi56/72, Hanzi32/44 va pinyin16/22 yaxshi asos, lekin screen override’lari parallel scale yaratgan.

**[P1/P2] Brand va status ranglari aralashadi.** [Dark palette][a-dark] Cinnabar rolini cyan #20BCEB’ga almashtiradi; [Theme:74][a-error] error’ni cinnabarDark orqali oladi, dark holatda u ham ko‘k. Brand, success va error alohida semantic rollarga muhtoj. Dark UI bu auditda runtime’da ko‘rilmagan.

**4. Mini App design-system implementation auditi**

Asosiy shell [course-v3.html][m-root] ichida CSS va render funksiyalari bilan qurilgan. Course, Practice, Voice, Rating va Profile shu shell’da. Lesson — #flow va renderFlowCard/card* funksiyalari. Dictionary, Onboarding va Subscription alohida HTML. Practice’ning hozirgi asosiy limit UI’i [course_v3_data/ads.js][m-limit-css] orqali inject qilinadi.

Course root’da 23 CSS variable bor, jumladan safe area va shell width. Ranglar tokenlangan, lekin umumiy radius, spacing va typography scale yo‘q.

Quyidagi hisob course-v3.html ichidagi style bloklariga tegishli, comment’lar chiqarilgan. Inline va JS-generated style’lar bu jadvalga kiritilmagan.

| CSS o‘lchovi | Deklaratsiya | Turli qiymat |
|---|---:|---:|
| border-radius | 267 | 32 declaration qiymati |
| font-size | 436 | 41 |
| font-weight | 201 | 7: 400/500/600/650/700/750/800 |
| line-height | 92 | 16 |
| letter-spacing | 17 | 12 |
| box-shadow | 35 | 35 |
| padding-*, margin-*, gap, row-gap, column-gap | 719 | 225 compound qiymat |
| Hex rang | 175 | 70 |

Spacing hisobida responsive, negative margin va dekor geometriyasi ham bor. Ularni hammasini “random spacing bug” deyish noto‘g‘ri. Ammo Today plan va list row’laridagi 7/9/10.5/11.5/13.5 kabi lokal qiymatlar named system o‘rniga ishlatilayotgani aniq.

**Barcha Course stylesheet border-radius declaration qiymatlari:** 0; 2px; 3px; 4px; 5px; 6px; 7px; 8px; 9px; 10px; 11px; 12px; 13px; 14px; 15px; 16px; 17px; 18px; 20px; 22px; 24px; 26px; 28px; 34px; 50%; 999px; inherit; 20px 20px 0 0; 22px 22px 0 0; 24px 24px 0 0; 4px 16px 16px 16px; 46% 54% 0 0/9% 9% 0 0.

[To‘liq radius inventari][inventory] Android main/direct/play va auditdagi Mini HTML/ads.js uchun 647 ta source occurrence’ni file, line, expression bilan beradi. CSS inline/JS fragmentlari raw declaration sifatida saqlangan; ular computed layout o‘lchovi emas.

**[P2] O‘qish kontrasti.** Literal tokenlardan hisoblangan ink3 #A89E8E / paper #FDF9F0 kontrasti 2.52:1. Bu [10px node meta va 11px nav label’larda][m-small] ishlatiladi. White/cinnabar 4.02:1; white/checkout green 3.61:1. Exact font size/background/state har control’da tekshirilishi kerak; bu to‘liq accessibility certification emas. V1 normal matn uchun kamida 4.5:1, katta matn uchun 3:1 ni talab qiladi. [W3C contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

**5. Har ekran bo‘yicha audit**

**Course / Home**

AI-template risk: **Android MEDIUM; Mini MEDIUM.** Android’da normal unlocked ekran uchun baho kodga asoslangan; access dialog real ko‘rildi.

Problems:

1. **[P2] Mandatory access blokida illustration va narx katta visual weight oladi.** [CourseScreen:505][a-course-gate] Hsk30LockedEntryDialog dismissible=false. Screenshotda kitob illustration’i va checkout CTA asosiy visual weight’ni oladi. Faqat unlock yoki HSK2’ga qaytish bor. Bu current locked-track state. PROJECT_MEMORY’dagi 2026-10-03 qarori bu blokni kursga kirishda majburiy ko‘rsatishni talab qiladi; gating va payment timing KEEP. Audit faqat ichki layout/readability haqida.
2. **[P1] Dekor va aktiv lesson birga e’tibor talab qiladi.** Android [TodayPlanCard][a-plan] qora surface, oltin action va “计” watermark ishlatadi. Mini [current node pulse][m-course-motion] hamda path Panda bob/nod animatsiyalari birga mavjud; Panda har beshinchi non-current node’da k%5===2 bilan qo‘yiladi, o‘quv ehtiyojiga bog‘lanmagan.
3. **[P2] Lokal shape/type/spacing.** Android Course’da 5/12/14/20/22/26dp radius; Mini Today plan’da 11.5px label, 10.5px caption, 13.5px CTA. Ularning semantik roli umumiy scale’da yo‘q.
4. **[P2] Gate presentation/exit parity tekshirilishi kerak.** Mini ham global HSK3 access gate qiladi; “Mini doim map ko‘rsatadi” degan farq mavjud emas. Ammo [Mini sheet][m-course-gate] close/backdrop/back bilan yopiladi, Android locked dialog yopilmaydi. Mini denied-map’dan keyingi yopilgan holat runtime’da tekshirilmagan. Yopilgan state access talabi yo‘qolishiga yoki blank screen’ga olib bormasin; mavjud approved exit actionlar saqlansin.

3–5 soniya hierarchy: locked screenshotda asosiy action tushunarli — unlock. O‘quvchi bugun nima o‘rganishi/erkin davom etish holati esa tushuntirishga muhtoj. Unlocked Course’da “current lesson / Today task” asosini saqlash kerak.

KEEP: real lesson order, unit/chapter progress, current lesson, Today plan, warm palette.

MODIFY: bitta “keyingi o‘quv qadam” ustuvorligi; qolgan XP/streak/meta pastroq weight; gate ichidagi o‘qish/action hierarchy; majburiy access talabi va approved exit actionlar bilan presentation parity.

REMOVE: vazifaga bog‘lanmagan path scenery/Panda takrori, bir vaqtda ko‘p infinite pulse, katta dekor watermark.

REDESIGN: locked-track presentation va active lesson composition. Entitlement yoki lesson order’ni o‘zgartirish bu auditning talabi emas.

**Practice**

AI-template risk: **Android MEDIUM; Mini HIGH.**

Problems:

1. **[P1] Tool katalogi learning hierarchy o‘rnini egallaydi.** Android [ToolRow][a-practice] va Mini [rowCard][m-practice] Dictionary, Recognition, Pronunciation, Tests, Mistakes’ni icon + title + subtitle + arrow formatida takrorlaydi. Tavsiya etilgan bitta mashq ajratilmaydi.
2. **[P2] Radius/spacing lokal.** Android radiuslari 7/11/12/13/14/16/18/999dp; 11dp list gap, 17dp hero padding, 13dp icon tile. Bu reusable role scale’dan kelmaydi.
3. **[P2] Rangli icon tile’lar kategoriya dekoriga aylanadi.** Amber/blue/jade/cinnabar bir xil vizual kuchda. Android PlacementCard qora/oltin va 84sp “级” watermark bilan alohida til yaratadi.
4. **[P2] Soon holati affordance’i.** Mini HSK3 tests card faol ko‘rinadi, “soon” bosilgandan keyin ochiladi. Available va unavailable tool state avvaldan farqlanishi kerak.

3–5 soniya hierarchy: qayerga kirish mumkinligi tushunarli; “hozir qaysi mashq foydali?” javobi yo‘q.

KEEP: mavjud drill turlari, qisqa izohlar, offline/server availability, reusable row funksiyasi.

MODIFY: bitta recommended practice; qolgan tool’lar grouped list; status badge va icon optik o‘lchami.

REMOVE: oddiy tool satrlaridagi alohida shadow/wash, katta funksiyasiz watermark.

REDESIGN: Practice home hierarchy; mashq natijalari va backend logic saqlanadi.

**Lesson**

AI-template risk: **Android MEDIUM/HIGH; Mini HIGH.**

Problems:

1. **[P1] Hanzi atrofidagi dekor qatlamlari ko‘p.** Android [HanziPlate/NewWordInfo][a-lesson] 22dp plate, 3dp border, 6dp depth, uchta sparkle, ikkinchi 18dp info card va chips ishlatadi. Mini [qcard/mix-review/nw-card][m-lesson] fake stacked cards, gradient, red/gold border va embossed shadow ishlatadi.
2. **[P1] Panda matn bilan joy uchun raqobat qiladi.** Mini beside coach 118×150px va prompt yonida turadi; 320px ekran uchun matn ustuni taxminan 156px bo‘lib qolishi mumkin. Bu uzun Chinese/RU/TJ prompt uchun source risk; real clipping ko‘rilmagan. Android [coach stage][a-lesson-screen] choice’da 124dp, pronunciation’da 150×165dp — reading/action nisbatini kichik ekranda tekshirish zarur.
3. **[P2] Chinese typography parallel scale’lar bilan ishlaydi.** Android Hanzi60/69, pinyin26/31, meaning17/25; shared Type’da boshqa qiymatlar. Mini Hanzi92/60/50/29/24px, pinyin26/17/14/13px. Turli pedagogik rol mumkin, lekin bu rollar tokensiz.
4. **[P1/P2] Mandatory reveal reading ritmini sekinlashtiradi.** Android NewWord’da 400ms +500ms keyin meaning/CTA ochiladi. Mini [presentation bridge][m-lesson-entry] minimum720ms va430ms exit ishlatadi. Yangi material audio sequencing’i foydali bo‘lishi mumkin; takroriy ko‘rishda majburiy kechikish ortiqcha.

3–5 soniya hierarchy: progress va primary check yaxshi. New word/long prompt holatida Hanzi→pinyin→ma’no o‘qish yuzasi tinchroq bo‘lishi kerak.

KEEP: lesson data/order, full sentence quiz’lar, Hanzi/pinyin/tarjima, progress, select→check, correct/wrong feedback, contextual coach. Android HskAnswerOption adoption’i yaxshi.

MODIFY: bitta reading surface; word/sentence/pinyin uchun named style; coach matn kengligini egallamasin.

REMOVE: sparkle/fake stack/repeated depth; qayta o‘qishda mandatory reveal.

REDESIGN: NewWord va Grammar composition, compact-height/long-prompt layout. Quiz javob algoritmi o‘zgarmaydi.

**AI Voice**

AI-template risk: **Android MEDIUM; Mini MEDIUM.**

Problems:

1. **[P2] Home bloklari turli til ishlatadi.** Real Android [VoiceBox][a-voice] qora hero + qizil CTA, keyin alohida gold quota card. Primary action aniq, ammo quota yetarlicha sokin meta sifatida qo‘shilishi mumkin.
2. **[P1/P2] Call/chat’da lokal glass hierarchy.** Mini [chat/dock][m-voice-chat] blur8px, translucent fill,22px radius va shadow ishlatadi; message radius15px/6px. Bu umumiy surface rollariga bog‘lanmagan.
3. **[P2] Panda har tab ochilishida pop qiladi.** [renderVoice][m-voice] effect’i yangi feedback bermaydi. Android screenshotdagi Panda esa suhbatdosh sifatida maqsadli.
4. **[P1] Android nav markazidagi AI label kesilgan.** Screenshotlarda tasdiqlandi. [MainScaffold][a-nav] 82dp pill minus12dp padding =70dp ichki joy; center halo62dp + line height bilan label sig‘maydi. -8dp offset yangi layout joyi ajratmaydi.

3–5 soniya hierarchy: Android home yaxshi — “Suhbatni boshlash” darhol tushunarli. Active recording/listening/processing/transcript holatlari uchun bitta barqaror signal scale kerak.

KEEP: Panda conversation partner, bitta start CTA, subtitles/transcript/corrections, real limit.

MODIFY: quota’ni primary action kontekstida meta qilish; chat va controls shared surface/type; navigation label layout.

REMOVE: takroriy tab-pop va keraksiz blur/shadow qatlamlari.

REDESIGN: active call state hierarchy; ovoz yoki AI pipeline o‘zgarmaydi.

**Dictionary**

AI-template risk: **Android MEDIUM; Mini MEDIUM.**

Problems:

1. **[P1/P2] Har word natijasi individual card.** Android [WordRow][a-dict] 14dp HskGlassSurface +5dp shadow. Mini [row][m-dict-row] 14px +3px/9px shadow. Uzoq ro‘yxat uchun divider row scan qilishni yengillashtiradi.
2. **[P2] Light palette yaqin, lekin aynan bir xil emas.** Course paper/red/secondary #FDF9F0/#E04A40/#665D50; [Dictionary light][m-dict-light] #FBF7EF/#C2403A/#6E665B. Light mode barcha root color va CJK family’ni override qiladi; “dark variable’lar sizib qoladi” degan muammo aniqlanmadi.
3. **[P1/P2] Alohida dictionary default’i boshqa identity.** Default entry navy/blue va CJK sans/gradient; Course kirishi theme=light’ni yuboradi. Bu ikki kirish holatini bir-biriga aralashtirmaslik kerak.
4. **[P2] Content type roli noto‘g‘ri reuse.** Android word Hanzi hanziSmall bilan chiziladi, shared Type comment’da bu node/league icon glyph roli. Mini tarjima13px nowrap/ellipsis; uzun RU/TJ ma’nolari kesilishi source risk.
5. **[P2] Inset parity.** Mini Dictionary root header/list fixed padding ishlatadi; Course/Onboarding’dagi Telegram contentSafeArea wrapper bilan bir xil emas.

3–5 soniya hierarchy: search→filter→results→detail tartibi yaxshi. Panda bu screen’da content ustiga qo‘yilmagan.

KEEP: Hanzi/pinyin/meaning, search/recents/filter, audio, stroke order/writing/detail.

MODIFY: shared palette, content Hanzi style, multi-line meaning allowance, safe-area wrapper.

REMOVE: har natija uchun glass/shadow va default dekor gradient.

REDESIGN: grouped list density va detail action hierarchy.

**Profile**

AI-template risk: **Android HIGH; Mini HIGH.**

Problems:

1. **[P1] Card hierarchy product hierarchy’ni almashtiradi.** Real screenshot: hero→subscription CTA→daily goal→to‘rtta stat tile→calendar→achievements. [ProfileScreen:189][a-profile] bu bloklarni alohida item/surface qiladi. Obuna learning progress’dan oldin juda kuchli ko‘rinadi.
2. **[P1] Mini’da ham uzun surface ketma-ketligi.** [renderProfile][m-profile] phero, pgoal, desktop promo, calendar card, achievements, Pro card, Mistakes/Friends row va social links yig‘adi. [Pro card][m-profile-pro] qora hero +会 watermark bilan billing’ni alohida kuchaytiradi.
3. **[P2] Repeated data.** Daily goal blokida streak va alohida Streak tile/calendar bir xil holatni yana qaytaradi. Buni bitta progress section’da birlashtirish mumkin.
4. **[P1/P2] Floating assistant kontent card’i bilan collision qiladi.** [AssistantHost][a-assistant] bubble’ni absolute y=.58*height atrofida joylashtiradi; screenshotda Streak tile o‘ng qismiga tushgan. Chapdagi raqam/matn yashirilgani tasdiqlanmagan, ammo ikkinchi AI control va card collision e’tiborni bo‘ladi.
5. **[P2] Bar orqali pastdagi kontent ko‘rinishi.** Screenshotda achievements floating bar ortida. Profile oxirida 16dp + LocalMainBottomInset mavjud; kontent unreachable yoki bottom padding yo‘q deb baholanmadi.

3–5 soniya hierarchy: “mening o‘qish progressim” bilan “obuna oling” birinchi e’tibor uchun raqobat qiladi.

KEEP: real account/progress, goal, calendar, achievements, plan state, settings.

MODIFY: learning progress first; billing compact status/action; metrics umumiy group; secondary account actions divider list.

REMOVE: takroriy stat card’lar, watermark/dekor, default floating assistant’ning content collision’i.

REDESIGN: Profile information hierarchy va assistant entry placement.

**Onboarding**

AI-template risk: **Android MEDIUM; Mini LOW/MEDIUM.**

Problems:

1. **[P2] Mustaqil type/shape implementations.** Android [ChoiceCard][a-onboarding] local selected #FFF3EF,14dp shape,17/25 speech text,13dp CTA; Mini [onboarding styles][m-onboarding] cards14px/bubble18px/CTA13px hamda650 weight ishlatadi.
2. **[P2] Muhim badge juda mayda.** Android active ChoiceCard’dagi NewBadge8sp. Course version/new status12sp semantic meta’ga o‘tishi kerak. Unused compact switch’dagi narxni active UI muammosi deb hisoblamadim.
3. **[P2/P3] Har choice’da character reaction.** Selection confirmation foydali, lekin kuchli harakat matn o‘qishdan ustun bo‘lmasin.
4. **[P2] Utility icon contract.** Android custom Canvas24px/2px round stroke; Mini custom SVG; boshqa screen’lar Material/Tabler. Custom illustration to‘g‘ri, ammo utility controls optik qoidasiz ajralib qolgan.

3–5 soniya hierarchy: bir savol va bitta footer action aniq. Bu ekranlar product flow jihatidan yaxshi.

KEEP: welcome→version→level→goal,3 savol progress, selected/radio state, meaningful notebook Panda, localization, adaptive layout, safe areas, reduced motion.

MODIFY: common typography/choice/button/badge tokens; Panda matnga xizmat qilsin.

REMOVE: selection’dagi kuchli takroriy motion; keraksiz unused lokal styling keyin alohida aniqlansin.

REDESIGN: to‘liq rewrite shart emas; V1 composition’ga moslash yetarli.

**Limit**

AI-template risk: **Android LOW/MEDIUM; Mini HIGH.**

Problems:

1. **[P1] Mini Practice limit mahsulot tilidan keskin chiqadi.** [ads.js:75][m-limit-css] #15120f full-screen, translucent gradient20px card, nested benefits/why/promo cards,78px gradient icon+glow, oq gradient CTA va blur close beradi. Hozir Recognition/Pronunciation/Mistakes/Tests shu [showLimitPromo][m-limit] orqali ishlaydi.
2. **[P1] Sababdan ko‘ra promo kuchli.** Limit promo carousel4500ms interval’da o‘zgaradi. User cheklov sababini va qachon davom etishini bilishi kerak bo‘lgan vaziyatda marketing harakati ustun.
3. **[P2] Bir nechta limit identity.** Mini Practice dark overlay, [Lesson paywall][m-paywall] warm sheet, Voice local UI, HSK3 book dialog. Android [LimitBlock][a-limit] boshqa sokin paper composition.
4. **[P2] Android local sizing/button.** LimitBlock26dp side/64dp vertical padding,94dp lock,26/34dp gap; shared button o‘rniga direct Material Button/OutlinedButton16dp. Bitta state scale yetishmaydi.

3–5 soniya hierarchy: Android headline→reason→primary→secondary aniq. Mini’da promo va nested surfaces sabab/action bilan raqobat qiladi.

KEEP: backend reason/reset/eligibility, dismissal, bitta subscription CTA, trial secondary. Android SectionLimitOverlay’da close bor; bu non-dismissible HSK3 dialogi bilan bir holat emas.

MODIFY: sabab→reset vaqt/foydalanish imkoniyati→keyingi action; shared state/button tokens.

REMOVE: rotating marketing carousel, glow/blur/dekor gradient, card ichidagi card.

REDESIGN: Mini limit composition va platformalararo semantic limit variants; access logic’ni saqlash.

**Subscription**

AI-template risk: **Android HIGH; Mini HIGH.**

Problems:

1. **[P1] Checkout yangi brand rangiga o‘tadi.** Real Android ekran green #0E9A64. [CheckoutColors][a-checkout] va [subscription.html root][m-sub] shu palette’da mos. Demak bu Android-vs-Mini rang farqi emas; ikkala platformada Course’dan checkout’ga ichki identity o‘zgarishi.
2. **[P1] Selection card’lar keragidan katta/ko‘p.** Real currency chooser beshta katta rounded card’ni dialog ichiga olgan. Mini’da plan/choice/quote/discount/benefit tile ketma-ketligi bor. Ayrim selection border’lari zarur, ammo benefits/meta uchun yana surface kerak emas.
3. **[P2] Type boshqa xarakter oladi.** Native27sp/Black headline va ko‘p Black/ExtraBold; Mini h1/section900, benefits850, badge950. Course body500–600 bilan vizual og‘irlik ajraladi.
4. **[P2] Local tokens.** Native checkout’da13/14/15/16/18/20/24dp radii va28 local hex rang; Mini18/13 radius token bor, lekin lokal exceptions qolgan.
5. **[P2] First decision hierarchy.** Screenshotda tariff ko‘rishdan oldin currency chooser katta modal bo‘lib ochilgan. Currency tanlash zarur bo‘lsa ham price context bilan ixchamroq bo‘lishi mumkin.

3–5 soniya hierarchy: active currency choice tushunarli; tariff/value/payment yo‘li uning ortida. Staged flow va sticky primary action yaxshi.

KEEP: server price/quote/discount/payment/referral logic, country/currency options, plan→method→payment→done, sticky primary.

MODIFY: shared brand/type/button; radio rows; grouped price summary; currency qarorini ixcham ko‘rsatish.

REMOVE: benefit tile’larning takroriy border’lari, dekor discount gradients, watermark.

REDESIGN: checkout presentation va choice density. Payment flow yoki sotiladigan entitlement o‘zgarmaydi.

**Completion / result**

AI-template risk: **Android HIGH; Mini HIGH.**

Problems:

1. **[P1] Natija va next action animatsiyadan keyin keladi.** Android [LessonCompletionCelebration][a-result] COMPLETE, optional STREAK va RANK_UP scene’larini ketma-ket tuzadi. CTA RevealedScene ichida; [FX timing][a-fx] LAND1240ms, FLY2900ms, ZOOM1060ms’dan keyin reveal. Bu motion-enabled holat; reduced-motion guard mavjud.
2. **[P1] Panda hierarchy’ni eng aniq shu yerda buzadi.** Reveal’dan oldin faqat cinematic character, keyin rays/confetti, corner character, emblem va stats ko‘rinadi. Kundalik natijaga bir nechta mandatory intro ortiqcha.
3. **[P1/P2] Mini’da ham celebration chain.** [showLevelUp/streak/rank][m-result] character entry va keyingi overlay’larni ishlatadi. Normal lesson Panda, checkpoint Dragon, streak superhero Panda — character role qoidasi markazlashtirilmagan.
4. **[P2] Result scale parchalangan.** Native StatTile14dp, RankRow12dp va inner9dp; Mini recognition/pronunciation/exam/placement/voice/course alohida renderer’lar. Common learned-outcome/result role yo‘q.

3–5 soniya hierarchy: natija kutish/reward orqali ochiladi; “nimani o‘rgandim va keyingi qadam nima?” darhol chiqishi kerak.

KEEP: real XP, accuracy, elapsed time, xatolar, transcript, milestone; uydirma award yo‘q.

MODIFY: learned outcome first; bitta primary next action; streak/rank compact summary; milestone optional.

REMOVE: routine completion’dagi2900ms cinematic entry, ketma-ket majburiy bayramlar, rays/glow/dekor overload.

REDESIGN: bitta result composition + qisqa milestone moment.

**6. Android vs Mini App inconsistency**

| Qatlam | Android | Mini App | Baho |
|---|---|---|---|
| Main light colors | Paper/cinnabar/ink semantic palette | Course root aynan shu | KEEP; mahsulotning umumiy asosi bor |
| Main navigation | Floating glass82dp,28dp radius,14dp shadow | Solid edge-fixed70px, top border | P1/P2 surface va spatial language farqi |
| Voice center |52dp button/62dp halo, “AI” |58px button, “AI Voice” | P2 label/emphasis parity; native clipping P1 |
| 5 asosiy tab | Course/Practice/Voice/Rating/Profile | Shu 5 bo‘lim | KEEP |
| Icons | Asosan Material Filled | Asosan Tabler outline | P2 optik/family parity |
| Hanzi | Platform generic Serif | Songti/STSong/Noto Serif fallback | Niyat mos; exact font/glyph parity kafolatlanmagan |
| RU/TJ/UZ | Default native font | System web font stack | Platform farqi tabiiy; role/weight/wrapping parity yo‘q |
| Radius/spacing | Mahalliy dp + shared partial styles | Mahalliy CSS px | P2 rollar bir xil token set’da emas |
| Dictionary | Core theme + glass rows | Own light near-match va own standalone dark | P2 palette; P1 conditional default identity |
| Limit | Paper LimitBlock + shared overlay | Dark/glow ads overlay va warm lesson paywall | P1 eng katta visual language uzilishi |
| Subscription | Green direct checkout | Green checkout | O‘zaro mos, main product bilan P1 palette split |
| HSK3 access gate | Mandatory locked dialog | Closable sheet | P2 presentation-state parity; mandatory entry qoidasi KEEP |
| Panda/motion | Native coach + cinematic FX | SVG/CSS/character pack + path dekor | P1 role/attention; P2 implementation rules |

Aniq glyph yo‘qolishi, RU/TJ matni real kesilishi yoki barcha screen’da icon’lar random ekani tasdiqlanmadi. Brand/social SVG va ta’limdagi “字” glyph’ni avtomatik muammo deb chiqarish kerak emas. Utility icons uchun bir xil optik qoida zarur.

**7. TOP 10 AI-LIKE PROBLEMS**

1. **P1 — Card hierarchy:** Profile, Practice va Dictionary’da content/section hierarchy o‘rniga ko‘p individual rounded surface.
2. **P1 — Generic glass default:** HskGlassSurface har informational row’ga shadow/wash/border beradi.
3. **P1 — Mini Limit glow/promo overlay:** dark gradient, nested cards, blur va rotating carousel asosiy product tilidan ajralgan.
4. **P1 — Section/theme identity split:** warm cinnabar Course, green checkout, cyan dark brand/error va standalone dictionary palette.
5. **P1 — Routine result cinematic chain:** foydali natija/CTA’dan oldin Panda entry va ketma-ket bayramlar.
6. **P1 — AI affordance’ning app-wide ustunligi:** raised red center nav va yana floating assistant; Course core mahsulot bo‘lsa ham AI eng kuchli doimiy signal. Native AI label clipping ham tasdiqlangan.
7. **P1/P2 — Panda dekor chastotasi:** har beshinchi node, tab pop, sparkle/coach effects; learning state bilan bog‘liq bo‘lmagan motion.
8. **P2 — Radius/spacing token drift:** bir xil component rollari yaqin, lekin har xil local qiymatlar bilan.
9. **P1/P2 — Typography/contrast fragmentation:** nomlanmagan Hanzi/pinyin/meta scale, juda kichik captions,2.52:1 inactive-nav/meta pair.
10. **P2 — Platform implementation drift:** floating vs edge nav, filled vs outline icons, locked dialog vs closable sheet, turli limit/result composition.

**8. KEEP / MODIFY / REMOVE / REDESIGN — umumiy qaror**

| KEEP | MODIFY | REMOVE | REDESIGN |
|---|---|---|---|
| Warm paper/cinnabar identity | Semantic shape/space/type tokens | Default informational glass/shadow | Profile hierarchy |
| Hanzi→pinyin→tarjima | Grouped lists/dividers | Decorative fake card stacks | Mini Limit composition |
| Course order/current lesson | Bir screen’da bitta primary action | Routine cinematic chain | NewWord/Grammar reading layout |
| Server-owned progress/access/pricing | Quiet XP/streak/meta | Repeated scenery/watermark/sparkles | Common result composition |
| Contextual Panda coach/partner | Character size/role contract | Navigation/tabdagi sababga bog‘lanmagan pop | Checkout choice density |
| Existing drills/feedback | Icon optics, labels, readable contrast | Rotating limit marketing carousel | Locked-track presentation parity |
| Safe areas/reduced-motion ishlagan joylar | Full reduced-motion coverage | Assistant content collision | Main nav layout/emphasis |

**9. HSK AI DESIGN LANGUAGE V1 — proposal**

Asosiy tamoyil: **o‘quv mazmuni birinchi, keyingi mashq ikkinchi, reward va xizmatlar yordamchi**. Iliq kitob sahifasi, aniq siyoh matn va cinnabar action HSK AI’ning hozirgi o‘ziga xos asosini kuchaytiradi. Boshqa product’ning navigation, mascot yoki gamification’ini ko‘chirish kerak emas.

Bu token va component qoidalari taklifi; implementation plan yoki kod o‘zgarishi emas.

| Radius token | Qiymat | Rol |
|---|---:|---|
| small |8dp/px | Compact badge, kichik utility surface |
| medium |12dp/px | Button, input, selectable row |
| large |20dp/px | Dialog/sheet, bir asosiy content group |
| pill |999 /50% | Status chip va circle; oddiy card uchun emas |

0 faqat edge-to-edge/square; asimmetrik sheet top corners large rolidan olinsin. Illustration geometriyasi UI radius scale’ga majburlanmasin.

**Spacing:** 4 asosli scale —4,8,12,16,24,32,48. Screen gutter16, compact relation8, item padding16, section gap24, major separation32.1px border va2px optical adjustment explicit exception. Safe-area insets va drawn illustration koordinatalari spacing token emas.8px gridga majburan barcha matn/glyph’ni sig‘dirish shart emas.

| Typography token | Size / line height | Weight / qoida |
|---|---|---|
| Screen title |24/32 |700 |
| Section title |20/28 |600 |
| Body |16/24 |400 |
| Label / action |14/20 |600 |
| Caption |12/16 |400 |
| Meta |12/16 |500; actionable matn disabled rangida bo‘lmasin |
| Hanzi display |56/72 |Serif; bitta yangi character/word |
| Hanzi focus |32/44 |Serif; word detail |
| Hanzi sentence |24/36 |Readable CJK; uzun prompt uchun natural wrap |
| Pinyin |16/24 |400; diacritics uchun yetarli line box |

Chinese display va Chinese sentence alohida rollar. RU/TJ/UZ bitta Latin/Cyrillic role scale’da; tarjima uppercase/tracking bilan bezatilmasin. Weight400/500/600/700 yetarli. Long localized strings uchun fixed-height text box yoki majburiy one-line ishlatilmasin. Minimum readable interface caption12; decorative glyph kattaligi bu cheklovga kirmaydi.

**Color hierarchy:** canvas #FDF9F0, raised #FFFFFF, ink #211D17, secondary #665D50, divider #EAE0CC. Brand cinnabar #E04A40 illustration/highlight uchun; kichik oq action matni uchun dark cinnabar #B23530 yoki kontrasti yetadigan action variant. Jade faqat success/mastered, gold faqat achievement/reward, blue faqat informational role. Error alohida semantic red; brand token’ga bog‘lanmasin. Muted text yangi accessible token olsin; #A89E8E dekor/disabled uchun. Dark mode shu semantic rollarni va cinnabar brand oilasini saqlasin. Checkout main brand action’ni ishlatsin; green payment success uchun qolishi mumkin.

**Surface hierarchy:** canvas→flat content→grouped list→temporary overlay. Informational block uchun border/shadow shart emas. Related data bitta group, ichida divider. Shadow faqat haqiqiy overlap/overlay yoki zarur sticky element uchun. Default glass, glow, background blur va dekor gradient ishlatilmasin; waveform/progress kabi meaningful visualization exception bo‘lishi mumkin.

**Button hierarchy:** screen’da bitta primary,52dp minimum hit height, medium radius; secondary neutral border48dp; tertiary text. Selected option button emas: radio/check + qisqa row. Danger explicit color+label. Loading action joyini saqlasin. “AI”, “Obuna”, “Boshlash” bir viewport’da bir xil dominant CTA bo‘lmasin.

**Icon rules:** utility icons24px grid,2px optical stroke, round caps; Android/Web equivalent glyph’lar. Filled icon faqat selected nav variant sifatida qoida bilan ishlatilishi mumkin. Emoji — nav/action icon o‘rniga emas; flag region content sifatida mumkin. Hanzi glyph va brand/social assets alohida content/brand rollari.

**Panda rules:** uch rol — onboarding guide, lesson feedback coach, Voice partner. Oddiy catalog/dictionary/profile metadata’da dekor Panda yo‘q. Prompt kengligini egallamasin; normal coach taxminan56–72dp, katta scene faqat onboarding/Voice uchun contentga qarab. Bir visible area’da bitta personaj. Panda yangi state/feedback borida javob beradi; har N lesson yoki har tab-open’da shunchaki effect bermaydi. Routine result’da next CTA darhol ko‘rinadi; milestone animation optional.

**Motion rules:** press100–150ms, selected/feedback150–220ms, screen transition200–280ms. Daily completion effect400ms atrofida yoki qisqaroq va action’ni bloklamasin. Infinite bounce/pulse/glow bo‘lmasin; breathing faqat Voice/avatar kerak bo‘lsa. Reduced motion CSS va native’da barcha decorative loop/entry’ni o‘chiradi. Progress/playback/loading motion ma’no ifodalasa saqlanishi mumkin.

**10. Keyin o‘zgarishi kerak bo‘lgan fayllar**

Bu ro‘yxat o‘zgarish doirasini ko‘rsatadi. Ish tartibi, patch reja yoki implementation ruxsati sifatida talqin qilinmasin.

| Fayl / component | Keyingi ko‘rib chiqish sababi |
|---|---|
| [Color.kt][a-colors], [Type.kt][a-type], [Theme.kt][a-theme] | Semantic color/type coverage, shape/spacing contract |
| [HskSurfaces.kt][a-surface], [HskButtons.kt][a-buttons], [HskStage.kt](</Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/components/HskStage.kt>) | Flat/grouped/overlay va action roles |
| [MainScaffold.kt][a-nav] | Center label,5 tab baseline/emphasis, overlay style |
| [AssistantHost.kt][a-assistant] | Content collision va contextual entry |
| [CourseScreen.kt][a-course-gate], [TodayPlanCard.kt][a-plan] | Active lesson/gate/dekor hierarchy |
| [PracticeScreen.kt][a-practice] | Recommended task + grouped tool catalog |
| [LessonCards.kt][a-lesson], [LessonScreen.kt][a-lesson-screen], [LessonChoiceCards.kt](</Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonChoiceCards.kt>) | Reading/coach/type layout; shared answers saqlansin |
| [DictionaryScreen.kt][a-dict] | Divider rows, content Hanzi token, action density |
| [VoiceScreen.kt][a-voice] | Quota/call/result composition |
| [ProfileScreen.kt][a-profile] | Progress/account/billing hierarchy |
| [OnboardingScreen.kt][a-onboarding], [OnboardingIcons.kt](</Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingIcons.kt>), [OnboardingPandaMascot.kt](</Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingPandaMascot.kt>) | Shared type/choices/icon contract |
| [LimitBlock.kt][a-limit], [SectionLimitOverlay.kt](</Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/limit/SectionLimitOverlay.kt>) | Shared state/button/spacing |
| [SubscriptionCheckoutHost.kt — direct][a-checkout] | Palette/type/choice surface parity; Play host alohida no-op ekanini hisobga olish |
| [LessonCompletionCelebration.kt][a-result], [PracticeCompletionHero.kt](</Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeCompletionHero.kt>), [HskCelebrationFx.kt][a-fx] | Immediate result/CTA va optional milestone |
| [course-v3.html][m-root] | Shared CSS token/component contract va main screens/flow/results |
| [hsk-lugat.html][m-dict-light] | Palette, rows, type va Telegram inset parity |
| [course_v3_onboarding.html][m-onboarding] | Shared onboarding roles |
| [subscription.html][m-sub] | Brand/type/selection density |
| [course_v3_data/ads.js][m-limit-css] | Limit renderer va injected CSS |
| [hsk-lesson-presentation.js][m-lesson-entry] va shu character asset oilasidagi CSS/JS | Role-based Panda size, reduced motion, non-blocking entry |

Course data, VOCAB/GRAMMAR, quiz/homework algorithms, result backend, Telegram SDK, subscription/payment/referral logic ushbu presentation auditi sabab o‘zgartirilmasligi kerak.

**11. Yakuniy repository holati**

**Audit snapshot’i (implementationdan oldin):** asosiy `/Users/kaijimima1234/Projects/HSK AI bot` checkout’ida ikki HSK3 PDF oldindan o‘chirilgan edi; u checkout o‘zgartirilmadi. `codex/local-ai` worktree `origin/main` baseline’dan toza yaratildi va shu audit hujjati hamda implementation rejasi qo‘shildi. Audit vaqtida UI patch yo‘q edi. Keyingi implementation holati [UI/UX plan](</Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/docs/ui-ux-plan-2026-10-05.md>)da yozilgan. Commit/push qilinmagan.

PROJECT_MEMORY/AI_RULES/AGENTS o‘rganildi. Graph report eski2209f26b snapshot ekanligi aniqlangan; source xulosalari joriy b35cb77 fayllaridan tekshirildi.

Foydalanuvchining 2026-10-05 ko‘rsatmasi bilan ikki skill bo‘yicha audit kengaytirildi va [lokal implementation plan](</Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/docs/ui-ux-plan-2026-10-05.md>) tayyorlandi. Dastlabki baseline audit UI patchlardan oldin bajarilgan; patch/verification holati implementation plan boshida yuritiladi.

**12. Ikki skill bo‘yicha qo‘shimcha conformity auditi**

Qo‘llangan manbalar: [hsk-ai-ui](</Users/kaijimima1234/.codex/skills/hsk-ai-ui/SKILL.md>) va [ui-ux-pro-max](</Users/kaijimima1234/.codex/skills/ui-ux-pro-max/SKILL.md>). Birinchisi learning/product cheklovlarini, ikkinchisi accessibility, touch, focus, motion, states va responsive sifat mezonlarini beradi.

ui-ux-pro-max uchun design-system qidiruvi va UX domain validation bajarildi. Generatorning Video-First Hero, indigo palette, Traditional Chinese TC font va vibrant block recipe’i HSK AI kontekstiga mos kelmadi. Ular qabul qilinmadi. Actual Kotlin Compose/static HTML stack saqlanadi; React Native yoki yangi icon/font kutubxonasiga ko‘chish taklif qilinmaydi.

Quyidagi dalillar source auditidan. Native hit-area expansion, haqiqiy screen reader, dark contrast, landscape va text scaling runtime’da hali to‘liq tasdiqlanmagan.

| Severity / skill rule | Aniq dalil | Rejalashtirilgan xavfsiz tuzatish |
|---|---|---|
| P1 · color-contrast | [HskStage:270][s-stage-button]: Paper/cinnabar3.83:1. [Lesson feedback:963][s-feedback]: Flame/FlameSoft1.93:1; Jade/JadeSoft2.89:1. Wrong next CTA Paper/Flame2.08:1 | Dekor accent’dan accessible text/button juftlarini ajratish; grading holatlarini saqlash |
| P1 · viewport-meta / dynamic-type | [Course:5][s-viewport], Dictionary/Subscription viewport zoom’ni cheklaydi | Zoom cheklovlarini olib tashlash, responsive wrap; writer gesture’larini tekshirish |
| P1 · touch-target-size (baseline) | [Course:245][s-touch] va shu CSS’da lesson close/pinyin30px, practice back32px, audio32/34px, writer close36px | Patch’da bot-return CTA, Dictionary til/daraja, lesson audio va ayrim Mini controls 44px’ga ko‘tarildi; qolgan flow’lar uchun Web minimum44px va native minimum48dp, real hit-area tekshiruvi ochiq |
| P1 · keyboard-nav / aria-labels | [Dictionary row:1090][s-dict-row] div+delegated click; [Profile:5881][s-profile-actions] div onclick; sheet/lesson close va speaker controls name’siz | Mavjud handler/data-idx’ni saqlab native button/link; localized action names |
| P1 · focus-management | [App.openSheet:1792][s-sheet] umumiy sheet semantics’ni olib tashlaydi, focus lifecycle yo‘q | Dialog label, focus capture/trap/restore, background isolation; mandatory HSK3 exit siyosati o‘zgarmaydi |
| P1 · voiceover-sr / language | [Course:2][s-lang] html lang=ru; uz/tj runtime tiliga sync yo‘q. Hanzi fragmenti language metadata’siz | documentElement.lang sync; Chinese fragment lang=zh-Hans; tarjima contenti saqlanadi |
| P1 · state-clarity | [Onboarding:1009][s-onb-select] radio role bor, selected semantics yo‘q; [native Dictionary:327][s-dict-filter] selected faqat rang | selectable/group/state semantics va non-color selected marker |
| P1 · progress feeling / voiceover-sr | [HskStage:284][s-progress] visual Boxes progress semantics’siz; [Mini flow:1250][s-flow-feedback] feedback/progress live/min-max-current yo‘q | Progress semantics va concise polite result/next-prompt announcement |
| P1 · color-not-only | [LessonCards:993][s-pairs] MatchPairs state rang/opacity; wrong400ms flash+haptic | Selected/matched/wrong accessible state va check/x; matching/heart algorithm o‘zgarmaydi |
| P1 · back-behavior | [MainActivity:985][s-onb-back] icon Back callback bor, system Back shu callbackga ulanmagan | Step>0 system Back’ni existing back callbackga ulash; step0 exit saqlansin; runtime’da tasdiqlash |
| P2 · disabled-states | [Mini:4431][s-answered] javobdan keyin pointerEvents=none; keyboard/reader enabled holat qoladi | disabled/selected/correct semantics. Flow.answered double grading’ni allaqachon to‘sadi |
| P2 · dynamic-type | [HskStage:261][s-stage-button] fixed52dp CTA, onboarding fixed54dp; dictionary footer one-line labels | heightIn(min), wrap/adaptive layout; fontScale1.3/1.5/2.0’da tekshirish |
| P2 · safe-area-awareness | [Onboarding:148][s-tg-inset] Telegram safe/content insets events’ni hisoblaydi; main/checkout/dictionary implementatsiyasi bir xil emas | Ishlayotgan inset helper’ni shared contract’ga aylantirish; fullscreen/keyboard checks |
| P2 · reduced-motion | [HskBrandLoader:41][s-loader] unconditional loops; Mini path/current pulse guard qisman | Static accessible loader state va shared reduced-motion policy; user-started stroke playback saqlansin |
| P2 · input-labels / error-feedback | Native Dictionary placeholder-only search; lesson/onboarding feedback liveRegion’siz | Persistent search label/semantics va qisqa polite feedback; duplicate announcement bo‘lmasin |
| P2 · error-recovery | [Subscription:1225][s-quote] quote error bor, direct retry yo‘q; back→next orqali recovery bor | Mavjud loadQuote’ga retry; busy guard; narx/to‘lov hisobini o‘zgartirmaslik |
| P1 · keyboard-nav / error-recovery | [Mini Rating:5238][s-rating] clickable div row; fetch failure card’da retry yo‘q | Semantic row va existing loadLatestRating/loadReferrals retry; real league/referral data saqlansin |

KEEP dalillari: Android HskAnswerOption selected/correct/wrong description beradi; oddiy quiz feedback icon+matn bilan color-only emas. Native Dictionary skeleton/retry/empty va detail→list/writing Back mavjud. Mini Dictionary filter semantics/live result count va detail scroll restore mavjud. Onboarding safe-area/focus/reduced-motion ishlagan. Subscription busy disable va persistent upload error mavjud. Besh tab skill limitiga mos. HSK3 entry gate product requirement.

Qo‘shimcha supporting-screen dalillari ham tekshirildi:

| Severity / skill | Dalil | Xavfsiz tuzatish |
|---|---|---|
| P1 · data trust | [RatingScreen:198][g-rating] va Mini referral failure’da null/error0/0 sifatida ko‘rinadi | Verified success bo‘lmasa unavailable state; haqiqiy0 saqlansin |
| P1 · color-contrast | Rating gold matni paper’da1.97:1, goldSoft’da1.82:1; [settings:788][g-settings] current qiymati disabled ink’da | Dark reward ink va active InkSecondary |
| P1 · layout / dynamic-type | [Profile settings:771][g-settings] ko‘p row+logout/unlink oddiy scrollsiz Column’da | Scrollable sheet body; landscape/fontScale runtime check |
| P1 · voiceover-sr | Native reminder Switch label merge’siz; Mini toggle checked semantics’siz | Localized label+checked state; existing confirmNotifOff saqlansin |
| P1 · state-clarity | Rating tabs native clickable Surface va Mini CSS.on bilan, selected semantics yo‘q | Role.Tab/selected yoki web equivalent;48dp/44px target |
| P1 · destructive feedback | [Profile:882][g-unlink] unlink bevosita logout/local-clear callbackga ulanadi | Localized consequence + confirmation; callback/endpoint o‘zgarmaydi |
| P2 · dynamic-type | [LinkScreen:410][g-auth] provider label unweighted, spacer weighted | Text weight/wrap va arrow uchun joy; katta font’da tekshirish |

Auth safe-area scroll,68dp provider target, error/wait/cancel/reopen va haqiqiy provider brandmarks KEEP. Mini identity unlink confirmation va native Rating Retry mavjud — KEEP.

[shot-course]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/android-course-gate.png
[shot-voice]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/android-voice.png
[shot-profile]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/android-profile.png
[shot-sub]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/android-subscription.png
[shot-auth-postpatch]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/android-auth-gate-postpatch.png
[shot-onboarding-user]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/android-onboarding-user-screenshot.png
[shot-mini-course]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/mini-course-auth-gate.png
[shot-mini-dict]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/mini-dictionary.png
[shot-mini-onboard]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/mini-onboarding.png
[shot-mini-sub]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/mini-subscription-currency.png
[shot-mini-detail]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/mini-dictionary-detail.png
[shot-mini-stroke]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/mini-dictionary-stroke-order.png
[inventory]: /Users/kaijimima1234/.codex/visualizations/2026/10/04/01a1070c-7d09-7a81-bf4d-fc0595846271/hsk-ai-audit/radius-inventory.csv
[a-gate]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/MainActivity.kt:891>
[a-colors]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/Color.kt:43>
[a-dark]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/Color.kt:79>
[a-type]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/Type.kt:14>
[a-theme]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/Theme.kt:37>
[a-error]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/Theme.kt:74>
[a-surface]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/components/HskSurfaces.kt:28>
[a-buttons]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/components/HskButtons.kt:43>
[a-nav]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/navigation/MainScaffold.kt:182>
[a-assistant]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/assistant/AssistantHost.kt:304>
[a-course-gate]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/course/CourseScreen.kt:505>
[a-plan]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/course/TodayPlanCard.kt:91>
[a-practice]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/practice/PracticeScreen.kt:317>
[a-lesson]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCards.kt:147>
[a-lesson-screen]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonScreen.kt:407>
[a-dict]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/dictionary/DictionaryScreen.kt:977>
[a-voice]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/voice/VoiceScreen.kt:294>
[a-profile]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt:189>
[a-onboarding]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingScreen.kt:996>
[a-limit]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/limit/LimitBlock.kt:61>
[a-checkout]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/direct/java/com/pomp/hskai/feature/subscription/SubscriptionCheckoutHost.kt:107>
[a-result]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCompletionCelebration.kt:103>
[a-fx]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/components/HskCelebrationFx.kt:301>
[m-root]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:17>
[m-small]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:126>
[m-course-motion]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:97>
[m-course-gate]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:1322>
[m-practice]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:4779>
[m-lesson]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:272>
[m-lesson-entry]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/assets/characters/hsk-lesson-presentation.js:34>
[m-voice]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:4794>
[m-voice-chat]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:1022>
[m-dict-light]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/hsk-lugat.html:181>
[m-dict-row]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/hsk-lugat.html:65>
[m-profile]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:5872>
[m-profile-pro]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:5698>
[m-onboarding]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course_v3_onboarding.html:28>
[m-limit-css]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course_v3_data/ads.js:75>
[m-limit]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course_v3_data/ads.js:442>
[m-paywall]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:5984>
[m-sub]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/subscription.html:11>
[m-result]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:1859>

[s-stage-button]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/components/HskStage.kt:261>
[s-feedback]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonScreen.kt:963>
[s-viewport]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:5>
[s-touch]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:245>
[s-dict-row]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/hsk-lugat.html:1090>
[s-profile-actions]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:5881>
[s-sheet]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:1792>
[s-lang]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:2>
[s-onb-select]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/onboarding/OnboardingScreen.kt:1009>
[s-dict-filter]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/dictionary/DictionaryScreen.kt:327>
[s-progress]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/components/HskStage.kt:284>
[s-flow-feedback]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:1250>
[s-pairs]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/lesson/LessonCards.kt:993>
[s-onb-back]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/MainActivity.kt:985>
[s-answered]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:4431>
[s-tg-inset]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course_v3_onboarding.html:148>
[s-loader]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/core/design/components/HskBrandLoader.kt:41>
[s-quote]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/subscription.html:1225>
[s-rating]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/app/static/course-v3.html:5238>
[g-rating]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/rating/RatingScreen.kt:198>
[g-settings]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt:771>
[g-unlink]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/profile/ProfileScreen.kt:882>
[g-auth]: </Users/kaijimima1234/.codex/worktrees/fce7/HSK AI bot/android/app/src/main/java/com/pomp/hskai/feature/auth/LinkScreen.kt:410>
