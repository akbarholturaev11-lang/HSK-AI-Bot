# ARCHITECTURE_DECISION.md — Daily Plan / Personalizatsiya

Holat: **MUZLATILGAN** (2026-09-05)
Branch: `codex/local-ai`
## Baseline (ish boshlanishidan OLDINGI holat)

Yangi ish bularni buzgan deb o'ylamang — hammasi oldindan mavjud:

| Test | Holat |
|---|---|
| `pytest tests -q --ignore=tests/e2e` | **3 failed, 632 passed** |
| `test_free_course_parts_are_level_aware` | PROJECT_MEMORY "Problem 2" |
| `test_unpaid_course_lesson_policy_includes_hsk1_checkpoint` | PROJECT_MEMORY "Problem 2" |
| `test_review_questions_use_only_same_category_answers_and_v2_material` | PROJECT_MEMORY "Problem 2" |
| `tests/e2e` → `test_course_v3_support_pages_render_real_static_data` | **oldindan yiqilgan** — `course_v3_memorize.html` da "1/8" deck qurilmayapti (`hsk_memo_pref=radical`, `char=你`). Bu ishga aloqasi yo'q: na commitlar, na o'zgarishlar `course_v3_memorize.html` yoki `memo.js` ga tegmagan. **Alohida tekshirilsin.** |

E2E faqat `venv_311/bin/python` da ishlaydi (`.venv` da playwright yo'q):
`venv_311/bin/python -m pytest tests/e2e -q`

Bu fayl — implementatsiya kontrakti. Kod yozishdan oldin o'qiladi, ish davomida
o'zgartirilmaydi. O'zgartirish kerak bo'lsa avval shu fayl yangilanadi.

---

## 1. Qaror: nima quriladi

Mini App uchun **server tomonda hisoblanadigan "Bugungi reja"**, mavjud kurs
tajribasi ustiga. Yangi Home mahsuloti emas. Android/Desktop UI bu bosqichda
o'zgarmaydi, lekin ayni server ma'lumotini kodsiz oladi.

### Qayta ishlatiladigan mavjud tizimlar

| Tizim | Roli |
|---|---|
| `CourseProgress` | Yagona avtoritar chiziqli progress (`completed_lessons_count`) |
| `course_mistakes` + `CourseMistakeService` | Yagona `observed_weakness` manbasi |
| `course_xp_events` + `CourseGamificationService` | Bajarish/sur'at **signali** (kanonik tarix emas) |
| `CourseMiniAppPracticeService` | Savol tanlash, ballash, xatoga yozish |
| `CourseMiniAppAccessService` + `CourseAccessPolicyService` | Yagona gating |
| `course_daily_window.local_day_key` | Mahalliy kun kaliti |
| `CourseMiniAppProfile` | `goal`, `daily_minutes`, `timezone_offset_minutes` |
| `course_v3_parts` | `total_parts`, `current_part`, `source_lesson_for_part` |
| `VoicePracticeService` (10 rol) | `voice_dialog` task |
| `CourseHskExamService` | `mock_exam` task |

### Yangi servislar (atigi 2 ta fayl)

1. `app/services/learning_signals.py` — **faqat o'qish, qaror yo'q, gating YO'Q**
2. `app/services/daily_plan_service.py` — sof funksiya: `build()` + `hydrate()`

`PersonalizationService` **qurilmaydi**. Agar kelajakda Daily Plan'dan tashqari
ikkinchi mustaqil personalizatsiya iste'molchisi paydo bo'lsa — o'shanda ajratiladi.

### Yangi DB — bitta migratsiya, 4 ustun, yangi jadval YO'Q

```
course_miniapp_profiles:
  preferred_focus    String(24)  nullable
  daily_goal_xp      Integer     nullable
  daily_plan_key     String(48)  nullable   # "v1:hsk1:2026-09-05"
  daily_plan_json    Text        nullable   # faqat task IDENTITY
```

---

## 2. Daily Plan qoidalari (o'zgarmas)

### Kun barqarorligi

```
day_key = f"v1:{level}:{local_day_key(profile.timezone_offset_minutes)}"

if profile.daily_plan_key == day_key:
    tasks = json.loads(profile.daily_plan_json)      # MUZLATILGAN
else:
    tasks = DailyPlanService.build(signals)          # kuniga ATIGI 1 marta
    profile.daily_plan_key  = day_key
    profile.daily_plan_json = json.dumps(tasks)

for t in tasks:                                      # HAR safar hisoblanadi
    t.done      = course_xp_events (activity_date == bugun) dan
    t.available = CourseMiniAppAccessService dan
```

- **Saqlanadigan:** faqat task identity (`{"t": "...", "ref": "..."}`), ~200 bayt
- **Hisoblanadigan:** `done`, `available`, `lock_reason`, matn, tarjima
- `daily_plan_key` ichida sxema versiyasi bor → deploy task shaklini o'zgartirsa
  eski JSON avtomatik bekor bo'ladi (migratsiyasiz, crashsiz)
- Band o'zgarsa (`hsk1→hsk2`) kalit mos kelmaydi → reja qayta quriladi

### Uchta qat'iy qoida

- **Q-A.** Kun ichida YANGI task hech qachon paydo bo'lmaydi. Reklama ko'rilgani,
  obuna sotib olingani, zaiflik o'zgargani — hech biri ro'yxatga element qo'shmaydi.
- **Q-B.** Muzlatilgandan keyin qulflangan task ro'yxatda QOLADI (kulrang, sababi
  bilan) va ALMASHTIRILMAYDI.
- **Q-C.** Daily Plan — **maqsad, gate emas**. Foydalanuvchi rejadan tashqari
  xohlagancha dars qila oladi; xarita hech qanday cheklanmaydi.

### Task atomlari (faqat shular)

`continue_lesson` · `mistake_review` · `skill_drill` · `mock_exam` · `voice_dialog`

Repoda real capability bo'lmasa yangi task turi **ixtiro qilinmaydi**.

### Element soni va kunlik XP maqsadi

| `daily_minutes` | 5 | 10 | 15 | 20 | 30 |
|---|---|---|---|---|---|
| tasklar | 1 | 2 | 2 | 3 | **4** |
| `daily_goal_xp` (avto) | 25 | 30 | 35 | 40 | 50 |

XP miqdorlari (mavjud kod): dars qismi 20 · xato takrori 5 · skill drill 8 ·
test/voice 10 · kunning birinchi faoliyatiga +5 bonus.

**Reja — pol, maqsad — shift.** 1 va 2 tasklik rejalar maqsadni to'liq
yopadi; 3-4 tasklik rejalarda maqsad biroz yuqori turadi, ya'ni 20/30
daqiqalik o'quvchi halqani to'ldirish uchun bitta qo'shimcha ish qiladi.
Bu ataylab: halqa avtomatik emas, biroz intilishli bo'lsin.

`30 → 4 task` (avval 3 edi): aks holda 20 va 30 daqiqa sozlamasi bir xil
natija berardi va sozlama ma'nosiz bo'lardi.

### Task berish sharti (issue vaqtida)

1. hozir ochiq bo'lishi kerak
2. user uni hozir boshlay olishi kerak
3. natijasi serverga yozilishi kerak
4. access/paywall qoidalariga zid bo'lmasligi kerak

---

## 3. Weighting formulasi

```
score(kategoriya) =
      observed_weakness(kategoriya)                     # course_mistakes: wrong - resolved
    + PRIOR_W * prior(preferred_focus, kategoriya) * decay(n)
    + GOAL_W  * goal_weight(goal, task_type)

decay(n) = max(0, 1 - n / 10)      # n = shu kategoriyadagi natijalar soni
```

- `preferred_focus` — **prior** (dalil yo'q paytdagi taxmin), ~10 natijadan keyin so'nadi
- `observed_weakness` — dalil, `course_mistakes` dan
- `goal_weight` — **so'nmaydi**, task turi vaznini o'zgartiradi
- `"none"` fokus → `prior = 0`, sof observed

### `preferred_focus` → skill mapping

| `preferred_focus` | Task | Izoh |
|---|---|---|
| `speaking` | `voice_dialog`, `skill_drill(pronunciation)` | bepulda voice umrda 1 sessiya |
| `listening` | `skill_drill(listening)` | 820 ta `listening_choice` kartasi bor |
| `vocabulary` | `skill_drill(characters)`, `mistake_review(word)` | |
| `grammar` | `skill_drill(writing)`, `mistake_review(grammar)` | ⚠️ `TRAINING_SKILLS["writing"]` aslida GRAMMATIKA kartalarini tanlaydi, ieroglif yozishni emas |
| `none` | — | sof observed |

### `goal` → xulq

| Goal | Voice roli (mavjud) | Task vazni | Real o'zgarish |
|---|---|---|---|
| `hsk_exam` | `teacher_li` | mock_exam ↑↑, mistake_review ↑ | HA |
| `daily_communication` | `friend` | voice ↑↑, pronunciation ↑, listening ↑ | HA |
| `travel` | `chen`, `seller` (Mini App'da hali yopiq) | voice ↑, listening ↑, vocabulary ↑ | HA |
| `work_china` | `manager_wang` (Mini App'da hali yopiq) | voice ↑, course ↑ | HA |
| `study_china` | `classmate` (Mini App'da hali yopiq) | course ↑↑, vocabulary ↑ | QISMAN — hozircha segmentatsiya |

### ⚠️ Skill drill cheklovi (2026-09-05 da o'lchandi)

Savol banki kichik bo'lganda skill filtri to'lmaydi va kod umumiy bankka
kengayadi. HSK1 uchun o'lchangan mos savollar ulushi:

| Joriy qism | listening | characters | pinyin |
|---|---|---|---|
| 1 | 1/8 | 6/8 | 1/8 |
| 5 | 4/10 | 10/10 | 3/10 |
| 30 | 10/10 | 10/10 | 10/10 |

Ya'ni yangi boshlovchiga "tinglash mashqi" deb va'da berib bo'lmaydi —
savollarning ko'pi tinglash bo'lmaydi. **4-bosqich qoidasi:** `skill_drill`
aniq skill bilan faqat bank uni qoplay olganda beriladi (mos ulush >= 70%),
aks holda umumiy `skill_drill` (skillsiz) beriladi. Bank o'lchovi
`_skill_match` bilan oldindan tekshiriladi — taxmin qilinmaydi.

⚠️ Mini App'da hozir atigi 2 persona ochiq: `friend` (bao) va `teacher_li` (li).
Qolgan 8 rolni ochish — UI o'zgarishi, alohida ruxsat kerak. Shu bo'lguncha
goal'ning asosiy ta'siri **task vazni** orqali.

---

## 4. `course_xp_events` chegarasi

### Ishonchli

- "Bugun nima bajarildi" (Daily Plan `done`) — `activity_date` **mahalliy** kun
- Sur'at: oxirgi 7/30 kunda nechta faol kun
- "Bu qismni tugatganman" — `activity_ref = "v3-part:{level}:{n}:complete"`,
  `UNIQUE(user_id, activity_ref)`, Mini App va Desktop/Android'da **bir xil**
- Faollik profili — `activity_type`
- Haftalik liga — `week_start`

### Ishonchsiz — ishlatilmaydi

- **Ball/sifat** — `xp` ichida `+5` streak bonusi va qat'iy baza bor. XP ≠ bilim.
- **Qayta bajarish soni** — UNIQUE tufayli ikkinchi marta yozilmaydi
- **Nechta savol to'g'ri** — bu yerda yo'q
- **Sarflangan vaqt** — yo'q
- **Kanonik progress** — band almashsa `completed_lessons_count` nolga tushadi,
  `xp_events` qoladi → ikkisi zid bo'lishi mumkin. `CourseProgress` avtoritar.
- **Eski qatorlar** — faqat `v3-part:` prefiksi mos kelganini o'qing

### Majburiy filtr

Sur'at hisoblashda **chiqarib tashlanadi**: `reward_chest`, `challenge_win`,
`challenge_tie`. Bular o'rganish emas, gamifikatsiya.

Faqat shular sanaladi: `lesson`, `test`, `training`, `mistake_review`, `voice`, `challenge`.

---

## 5. Hozir QURILMAYDI

- `PersonalizationService` alohida qatlam
- `daily_plans` jadvali
- per-part attempt/score jadvali
- `course_mistakes` ga `listening` kategoriyasi migratsiyasi
  (tinglash `material_json.format` dan chiqariladi)
- Reja yo'lida LLM (AI byudjeti — `PROFIT_MARGIN = 0.5`)
- Android/Desktop UI
- Yangi voice personalar
- Yangi Home mahsuloti
- `main.py` katta refaktori (lekin **yangi mantiq u yerga yozilmaydi**)
- Botning `DailyPracticeService` / `CourseEngineService` ga tegish

---

## 6. Implementatsiya ketma-ketligi

### Joriy holat (2026-09-05)

| Bosqich | Holat | Commit |
|---|---|---|
| 0 — Muzlatish | ✅ | `f606866a` |
| 1 — DB poydevori | ✅ | `374daa8d` |
| 2a — Progress oynasi nuqsoni | ✅ | `892ef184` |
| 2b — Mini App mashq endpointlari | ✅ | `4c9dcf3c` |
| 2c — Signal ulanishi (talaffuz/tanish/yodlash) | ✅ | `a66c9b1d`, `b55e1aff`, `a4c727a8` |
| 3 — Onboarding + XP maqsadi | ⏸ UI ruxsati kutilmoqda | — |
| 4 — LearningSignals + DailyPlanService | ⏳ | — |
| 5 — `today` bloki | ⏳ | — |
| 6 — Mini App "Bugungi reja" | ⏳ UI ruxsati | — |
| 7 — Responsive | ⏳ UI ruxsati | — |
| 8 — Yakunlash | ⏳ | — |

Test: **707 passed** (baseline 632), ma'lum 3 ta failure o'zgarmagan.
E2E: **41 passed**, 1 oldindan yiqilgan.

### 2c dagi rejadan chekinish (sabab bilan)

Dastlabki reja "recognition/memorize savollarni serverdan olsin" edi. Kod
tekshirilgach bu **mumkin emasligi** aniqlandi:

- `recognition` — pinyin+ma'no ko'rsatib 4 ta ieroglif plitkasidan tanlatadi;
  serverning umumiy savoli esa oddiy matn variantlari beradi (plitkada pinyin
  yo'q). Ulash ekranni butunlay almashtirishni talab qilardi.
- `memorize` — umuman MCQ emas: `memo.js` dagi chiziq tartibi/radikal modeli.

Shuning uchun ikkala ekran **o'z oqimida qoldi**, natija esa darslar uchun
allaqachon ishlatiladigan qoida bilan yoziladi: mijoz faqat xato ieroglifni
aytadi, server uni o'z lug'atidan qayta quradi
(`CourseDrillSignalService` + `POST /api/v3/practice/report`).

Lug'at qoplami o'lchandi: `hsk-words.js` dagi 341 bir belgili so'zdan **340
tasi** serverda mavjud, ya'ni deyarli hamma xato tekshiriladi.

`/api/v3/practice/start|complete` (2b) esa **6-bosqichdagi `skill_drill`
task uchun** backend bo'lib qoladi — o'sha yerda yangi umumiy drill ekrani
kerak bo'ladi.

Har bosqich oxirida: `pytest tests -q --ignore=tests/e2e` → **3 ta ma'lum
failure'dan boshqa hammasi yashil** bo'lishi shart. Har bosqich alohida commit,
har bosqich oxirida ilova ishlaydigan holatda.

### BOSQICH 0 — Muzlatish (kodsiz) ✅

- [x] Baseline: `3 failed, 632 passed`
- [x] Bu fayl
- [x] **Qaror A** — gate egaligi: *limit o'zgarmaydi* (7-bo'limga qarang)
- [x] **Qaror B** — bepul reja: *reklamali tasklar cheklanmaydi* (7-bo'limga qarang)

### BOSQICH 1 — DB poydevori (xulq o'zgarmaydi)

**Fayllar:**
- `alembic/versions/0071_course_daily_plan.py` (yangi)
- `app/db/models/course_miniapp_profile.py`
- `app/services/course_miniapp_profile_service.py`
- `tests/test_course_miniapp_profile_preferences.py` (yangi)

**Nima:**
- 4 ta nullable ustun
- `COURSE_PREFERRED_FOCUS = {"speaking","listening","vocabulary","grammar","none"}`
- `validate_preferences` ga `preferred_focus` (ixtiyoriy, default `"none"`)
- `daily_goal_xp` default `daily_minutes` dan: 5→20, 10→40, 15→60, 20→80, 30→120
- `save_preferences` orqaga mos kengaytiriladi

**Xavf:** past. Hech qanday xulq o'zgarmaydi.
**Commit:** `feat(course): profil preferensiya va kunlik reja ustunlari (0071)`

### BOSQICH 2 — Signal: Mini App mashqlarini serverga ulash

**2a — mavjud nuqsonni tuzatish**
- `app/services/course_miniapp_practice_service.py`: `start()` va `complete()`
  `max_lesson` uzatsin — `source_lesson_for_part(level, completed_parts + 1)`.
  Hozir uzatilmaydi → savollar o'rganilmagan darslardan keladi.
  `CourseChallengeService` allaqachon to'g'ri qiladi — o'sha namunani ol.
- `tests/test_course_miniapp_practice.py` ga case
- **Commit:** `fix(course): mashq savollari o'rganilmagan darslardan kelmasin`

**2b — Mini App endpointlari (main.py ga EMAS)**
- `app/api/miniapp_practice.py` (yangi router): `/api/v3/practice/start`, `/api/v3/practice/complete`
- Telegram `initData` auth (`extract_verified_webapp_user_id`)
- Gate: mavjud `daily-gate` / `ad-gate` klientda chaqiriladi (o'zgarmaydi);
  `CourseMiniAppPracticeService.start()/complete()` ga `gate_checked=True`
  uzatiladi va servis `_gate()` ni chaqirmaydi (Qaror A)
- `app/main.py` da faqat `include_router` qatori
- **Commit:** `feat(course): Mini App mashq natijalari server tomonda yoziladi`

**2c — Klient ulanishi (UI o'zgarmaydi)**
- `app/static/course_v3_recognition.html` — savollar serverdan, javoblar serverga
- `app/static/course_v3_memorize.html` — shu
- `app/static/course_v3_pronunciation.html` — ball allaqachon serverda, faqat
  `complete` ga natija yoziladi
- **Commit:** `feat(course): mashq bo'limlari server savol bankidan ishlaydi`

**Xavf:** o'rta-yuqori (monetizatsiya + UX). Qaror A siz boshlanmaydi.

### BOSQICH 3 — Onboarding (4 javob) + haqiqiy maqsad halqasi ⚠️ UI ruxsati

- `app/static/course_v3_onboarding.html`: 3 ekran / 4 javob
  (1: daraja · 2: maqsad · 3: kunlik vaqt + fokus)
- Barcha matn **uz/ru/tj**
- `app/services/course_miniapp_onboarding_service.py`: `preferred_focus` qabul qilish
- `/api/miniapp/onboarding` payload kengaytmasi (mavjud endpoint)
- `/api/v3/map` javobiga `user.daily_goal_xp`, `user.preferred_focus`
- `course-v3.html`: `dailyGoal` serverdan; `App.pickGoal` serverga yozadi
  (hozir hech qayerga saqlanmaydi — halqa yolg'on)
- **Commit:** 2 ta (`feat(course): onboarding maqsad/vaqt/fokus so'raydi`,
  `feat(course): kunlik XP maqsadi server tomonda saqlanadi`)

### BOSQICH 4 — LearningSignals + DailyPlanService (UI yo'q)

- `app/services/learning_signals.py` — faqat o'qish, **gating YO'Q**
- `app/services/daily_plan_service.py` — sof funksiya
- `tests/test_learning_signals.py`, `tests/test_daily_plan_service.py`
  (mock session, DB kerak emas — `test_course_gamification_service.py` namunasi)
- **Xavf:** past (hali hech kim chaqirmaydi)
- **Commit:** `feat(course): LearningSignals va DailyPlanService`

### BOSQICH 5 — `today` bloki server javoblarida

- `app/main.py` `/api/v3/map` → `data["today"] = ...` (5-10 qator, mantiq servisda)
- `app/services/desktop_course_service.py` `course_map()` → ayni blok
- Android avtomatik oladi (`AndroidCourseService` merosxo'r)
- `tests/test_desktop_course_api.py`, `test_android_course_api.py` kontrakt testi
- **Xavf:** past — klientlar bilmagan maydonni e'tiborsiz qoldiradi
- **Commit:** `feat(course): kunlik reja map javobida (Mini App + Android + Desktop)`

### BOSQICH 6 — Mini App UI "Bugungi reja" ⚠️ UI ruxsati

- `course-v3.html`: kurs ekranida `.pwrap` dan keyin `renderToday()` kartasi
- 3 tilda
- `tests/e2e/test_miniapp_smoke.py` yangilanadi
- **Commit:** `feat(course): Mini App bosh ekranida Bugungi reja`

### BOSQICH 7 — Responsive ⚠️ UI ruxsati

- `--shell` CSS o'zgaruvchisi; 20 ta qattiq `max-width:480px` almashtiriladi
- `@media (min-width:900px)` — **faqat kurs ekrani** 2 ustun
- `.flow` (dars o'qish kengligi) hech qachon kengaymaydi
- Pastki nav shell ichida markazda qoladi (sidebar QILINMAYDI)
- **Commit:** `feat(miniapp): Telegram Desktop uchun adaptiv layout`

### BOSQICH 8 — Yakunlash

- `pytest tests -q` — to'liq
- Playwright e2e smoke
- Real tekshiruv: ilova haqiqatan ishlayotganini ko'rsatish
- `graphify update .`
- `PROJECT_MEMORY.md` yangilash (AI_RULES formatida)
- Release feedback draft (AGENTS.md qoidasi — user ko'radigan katta update)
- **Faqat shundan keyin** `main` haqida gap boradi

### PUSH QOIDASI (2026-09-05, foydalanuvchi ko'rsatmasi)

**Ish tugamaguncha `main` ga push YO'Q.** Barcha bosqichlar `codex/local-ai`
branchida, faqat lokal commitlar bilan. `main` ga chiqarish — butun ish
tugab, real testlar o'tkazilib, ishlayotganiga to'liq ishonch hosil
qilingandan keyin va faqat foydalanuvchi aytganda. Oraliq bosqichda push
qilinmaydi.

---

## 7. Qabul qilingan qarorlar (2026-09-05)

### Qaror A — Mini App mashq gate egaligi → **LIMIT O'ZGARMAYDI**

Mini App o'zining `daily-gate` / `ad-gate` yo'lida qoladi: bepul foydalanuvchiga
`recognition` / `memorize` / `pronunciation` kalitlari bo'yicha **umrda 1 marta**.

`CourseMiniAppPracticeService.start()` va `complete()` ga
`gate_checked: bool = False` parametri qo'shiladi. `True` bo'lganda servis
`_gate()` ni **umuman chaqirmaydi** — ruxsat chaqiruvchi tomonda tekshirilgan
deb hisoblanadi. Android/Desktop yo'li o'zgarmaydi (`gate_checked=False`).

Natija: monetizatsiya 1:1 saqlanadi, faqat savol tanlash, ballash va xatoga
yozish serverga o'tadi. `training_test` sloti Mini App drillari tomonidan
yeyilmaydi, ya'ni Xatolar bo'limi va Test markazi jimgina yopilib qolmaydi.

"Known Problem 3" (Mini App umrbod vs Android kunlik) **ataylab ochiq qoladi** —
bu alohida biznes qarori, bu ishga qo'shilmaydi.

#### Fon: nega bu muhim edi

| | Mini App bugun | `CourseMiniAppPracticeService` |
|---|---|---|
| Bepul limit | `lifetime=True` → **umrda 1 marta** | `lifetime` yo'q → **kuniga 1 marta** |
| Feature kaliti | `recognition`, `memorize`, `pronunciation` | `training_test` yoki `placement` |

`training_test` slotini `mistake_review` va Test markazi ham bo'lishadi.
Ya'ni to'g'ridan-to'g'ri ulash bepul foydalanuvchining Xatolar bo'limini
jimgina yopib qo'yishi mumkin.

### Qaror B — Bepul foydalanuvchi rejasi → **REKLAMALI TASKLAR CHEKLANMAYDI**

Reklama bilan ochiladigan har qanday task `available` hisoblanadi va rejaga
tushaveradi. Reklamali elementlar soniga chegara qo'yilmaydi.

`DailyPlanService.hydrate()` da task holati uch xil bo'ladi:
`open` (to'liq ochiq) · `ad` (reklama bilan ochiladi) · `locked` (obuna kerak).
`ad` — **berilishi mumkin**, `locked` — berilmaydi (issue vaqtida).

#### Qabul qilingan xavf

Bepul limitlar (tekshirilgan): `recognition` / `memorize` / `pronunciation` /
`placement` / `training_test` — har biri **umrda 1 marta**; voice — **umrda 1
sessiya**; darslar — hsk1/hsk2 da 1-darsning qismlari, hsk3/hsk4 da 2 qism.

Ya'ni ~3-kundan boshlab bepul foydalanuvchining rejasi to'liq reklamali bo'lishi
mumkin. Bu ataylab qabul qilingan.

**8-bosqichda kuzatiladigan metrika:** bepul foydalanuvchida reja `0/N` bilan
tugagan kunlar ulushi. O'sib ketsa — `hydrate()` da bitta konstanta bilan
(`MAX_AD_TASKS`) cheklash mumkin, arxitektura o'zgarmaydi.
