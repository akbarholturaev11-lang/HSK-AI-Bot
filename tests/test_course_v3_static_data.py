import json
import unittest
from pathlib import Path


BASE = Path("app/static/course_v3_data")
# Har HSK darsi 3-4 so'zlik mini-darslarga (qismlarga) bo'lingan; sonlar —
# flat qismlar soni (parts_manifest.json bilan mos bo'lishi ham tekshiriladi).
EXPECTED_LESSON_COUNTS = {
    "hsk1": 63,
    "hsk2": 72,
    "hsk3": 109,
    "hsk4": 181,
}
EXPECTED_SOURCE_LESSONS = {
    "hsk1": 15,
    "hsk2": 15,
    "hsk3": 20,
    "hsk4": 20,
}


class CourseV3StaticMapTests(unittest.TestCase):
    def test_level_maps_cover_all_lessons_without_demo_progress(self):
        for level, expected_count in EXPECTED_LESSON_COUNTS.items():
            with self.subTest(level=level):
                data = json.loads((BASE / f"{level}.json").read_text(encoding="utf-8"))
                lessons = [
                    lesson
                    for unit in data.get("units", [])
                    for lesson in unit.get("lessons", [])
                ]

                self.assertEqual(data["schema_version"], 2)
                self.assertEqual(data["level"], level)
                self.assertEqual(data["progress"]["xp"], 0)
                self.assertEqual(data["progress"]["completed"], 0)
                self.assertEqual(len(lessons), expected_count)
                # Unit = bitta HSK darsligi darsi; oxirgi tugun — checkpoint.
                self.assertEqual(len(data["units"]), EXPECTED_SOURCE_LESSONS[level])
                for unit in data["units"]:
                    self.assertTrue(unit["lessons"], unit.get("no"))
                    self.assertTrue(unit["lessons"][-1].get("checkpoint"), unit.get("no"))

                manifest = json.loads(
                    (BASE / "parts_manifest.json").read_text(encoding="utf-8")
                )[level]
                self.assertEqual(manifest["total_parts"], expected_count)
                self.assertEqual(
                    [l["n"] for l in lessons], list(range(1, expected_count + 1))
                )

                self.assertEqual(lessons[0]["status"], "current")
                for lesson in lessons[:3]:
                    self.assertFalse(lesson.get("locked_premium", False))
                    self.assertTrue((BASE / level / f"lesson_{lesson['n']:02d}.json").exists())
                for lesson in lessons[3:]:
                    self.assertEqual(lesson["status"], "locked")
                    self.assertTrue(lesson.get("locked_premium", False))
                    self.assertTrue((BASE / level / f"lesson_{lesson['n']:02d}.json").exists())

    def test_course_v3_respects_selected_level_and_real_invite_format(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        onboarding = Path("app/static/course_v3_onboarding.html").read_text(encoding="utf-8")

        self.assertIn("getSelectedLevel()", html)
        self.assertIn("localStorage.getItem(\"hsk_v3_level\")", html)
        self.assertIn('"/api/v3/map?lang="+LANG+"&level="+lv', html)
        self.assertIn("if(!INIT_DATA){showAuthGate();return;}", html)
        self.assertIn("function lessonDataUrl(lv,n)", html)
        self.assertIn('"/course_v3_data/"+normalizeLevel(lv)+"/lesson_"+String(Number(n)||0).padStart(2,"0")+".json"', html)
        self.assertIn("levelPicker:function", html)
        self.assertIn("/api/v3/invite?lang=", html)
        self.assertNotIn("start=ref_", html)
        self.assertIn("PRONOUNCE_LIMIT_EXCEEDED", html)
        self.assertIn("v3_pronunciation_limit", html)
        self.assertIn("Reklama bilan davom etish", html)
        self.assertIn("/api/v3/ad?placement=", html)
        self.assertIn("/api/v3/ad/view", html)
        self.assertIn("/api/v3/lesson/unlock", html)
        self.assertIn("section_completed", html)
        self.assertIn("ratingCountdownText()", html)
        self.assertIn("pendingRankUp", html)
        self.assertIn("loadLatestRating()", html)
        self.assertIn("rank:Number(u.rank||0)", html)
        self.assertIn("referralUsers=[]", html)
        self.assertIn("openRatingUser('+i+',\\'referrals\\')", html)
        self.assertIn("invitePayloadUrl()", html)
        self.assertNotIn("u.weeklyXp||u.xp||0", html)
        self.assertNotIn("meU.weeklyXp||MAP&&MAP.progress&&MAP.progress.xp", html)
        self.assertIn("awarded_xp", html)
        self.assertNotIn('["+60","XP"]', html)
        self.assertNotIn('["+200","XP"]', html)
        self.assertNotIn('["+50",lu.bonusXp]', html)
        self.assertNotIn("64 / 100", html)
        self.assertNotIn("2'+(LANG", html)
        self.assertIn("AdFlow", html)
        self.assertIn('event:"checkout_opened"', html)
        self.assertIn("CHECKOUT_NAVIGATING", html)
        self.assertIn('"&sid="+encodeURIComponent(COURSE_SESSION_ID)', html)
        self.assertIn('["course-v3",COURSE_SESSION_ID,event', html)
        self.assertNotIn('sessionStorage.getItem("hsk_v3_session_id")', html)
        subscription = (Path(__file__).parent.parent / "app" / "static" / "subscription.html").read_text(encoding="utf-8")
        self.assertIn('event:"/api/subscription-miniapp/event"', subscription)
        self.assertIn("CHECKOUT_ATTEMPT_ID", subscription)
        self.assertIn("attempt_id:state.attemptId", subscription)
        self.assertIn('trackSubscriptionStage("payment_instructions_viewed")', subscription)
        self.assertIn('trackSubscriptionStage("payment_receipt_selected")', subscription)
        self.assertIn("lockedValueText", subscription)
        self.assertIn("/api/miniapp/onboarding", onboarding)
        self.assertIn("onboarding_started", onboarding)
        self.assertIn('query.set("autostart","1")', onboarding)
        self.assertIn('activation_variant:"direct_start_v1"', onboarding)
        self.assertIn('if(sp.get("autostart")==="1")', html)
        self.assertIn('sp.delete("autostart")', html)
        self.assertIn("hsk_v3_lesson_resume:", html)
        self.assertIn("loadLessonResume(lv,l.n,Flow.queue.length)", html)
        self.assertIn("clearLessonResume((MAP&&MAP.level)||\"hsk1\",cur&&cur.n)", html)
        self.assertIn('lang:LANG,session_id:COURSE_SESSION_ID', html)

    def test_interactive_cards_present_and_level_gated(self):
        """New Duolingo-style cards (sentence_builder, listening_choice,
        dialog_cloze) appear and only use already-learned vocabulary.

        Qismlarga bo'lingandan keyin: har QISM 2-4 yangi so'z o'rgatadi (yoki
        checkpoint — 0 yangi so'z, dialog bilan yakunlaydi); tinglash va dialog
        to'ldirish har HSK darsining qismlar guruhida albatta bor."""
        manifest = json.loads((BASE / "parts_manifest.json").read_text(encoding="utf-8"))
        known_words: set[str] = set()
        known_lines: set[str] = set()
        for level in ("hsk1", "hsk2", "hsk3", "hsk4"):
            for src_lesson in manifest[level]["lessons"]:
                group_types = set()
                for n in src_lesson["parts"]:
                    data = json.loads(
                        (BASE / level / f"lesson_{n:02d}.json").read_text(encoding="utf-8")
                    )
                    where = f"{level}/lesson_{n:02d}"
                    is_checkpoint = n == src_lesson["checkpoint"]
                    self.assertEqual(data["checkpoint"], is_checkpoint, where)
                    self.assertEqual(data["source_lesson"], src_lesson["src"], where)
                    # dialoglar har qismda to'liq ma'lumotnoma sifatida turadi
                    lesson_lines = {
                        ln["zh"]
                        for b in data["dialogues"]
                        for ln in b["dialogue"]
                        if ln.get("zh")
                    }
                    cards = [c for sec in data["sections"] for c in sec["cards"]]
                    new_words = [c["word"]["zh"] for c in cards if c["type"] == "active_word"]
                    if is_checkpoint:
                        self.assertEqual(new_words, [], where)
                    else:
                        self.assertTrue(2 <= len(new_words) <= 4, f"{where}: {len(new_words)} new words")
                    part_words = {w["zh"] for w in data["active_words"]}
                    gate_words = known_words | part_words
                    gate_lines = known_lines | lesson_lines

                    for c in cards:
                        group_types.add(c["type"])
                        if c["type"] == "sentence_builder":
                            ans = c["answer_tokens"]
                            self.assertTrue(2 <= len(ans) <= 8, where)
                            for tok in ans:
                                self.assertIn(tok, c["tokens"], where)
                                self.assertIn(tok, gate_words, f"ungated builder token in {where}")
                            for lang in ("uz", "ru", "tj"):
                                self.assertTrue(c["sentence"].get(lang), where)
                        elif c["type"] == "listening_choice":
                            self.assertEqual(
                                c["options"][c["correct_index"]], c["audio_text"], where
                            )
                            # Listening cards come in two gated flavors: dialogue
                            # LINES or single WORDS (both only already-learned).
                            gate_listen = gate_lines | gate_words
                            for op in c["options"]:
                                self.assertIn(op, gate_listen, f"ungated listen option in {where}")
                        elif c["type"] == "dialog_cloze":
                            blanks = [ln for ln in c["lines"] if ln["blank"]]
                            self.assertEqual(len(blanks), 1, where)
                            self.assertIn(
                                c["options"][c["correct_index"]], gate_lines, where
                            )

                    known_words |= part_words
                    known_lines |= lesson_lines

                # Har HSK darsi (qismlar guruhi) interaktiv bo'lib qoladi:
                # tinglash + dialog to'ldirish.
                where = f"{level}/src_{src_lesson['src']}"
                self.assertIn("listening_choice", group_types, where)
                self.assertIn("dialog_cloze", group_types, where)

    def test_hsk_exam_uses_server_material_and_server_grading(self):
        html = Path("app/static/course_v3_test.html").read_text(encoding="utf-8")
        ads = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")

        self.assertIn('fetch("/api/v3/exams/start"', html)
        self.assertIn('fetch("/api/v3/exams/complete"', html)
        self.assertIn("selected_index:k", html)
        self.assertNotIn('fetch("/course_v3_data/exams/"', html)
        self.assertIn('if(!o.ok||!o.j||!o.j.ok){showEmpty();return}', html)
        self.assertIn("document.documentElement.lang=LANG", html)
        self.assertIn('back:"Kursga qaytish"', html)
        self.assertNotIn('localStorage.setItem("hsk_v3_level",level)', html)

        mistakes = Path("app/static/course_v3_mistakes.html").read_text(encoding="utf-8")
        self.assertIn('category="+encodeURIComponent(ACTIVE_CAT)', mistakes)
        self.assertIn("MISTAKE_PAGE.has_more", mistakes)
        self.assertIn("q.audio_text", mistakes)
        self.assertIn("access_ref:accessRef", html)
        self.assertIn("ad_supported:!!adSupported", html)
        self.assertIn('CourseAds.play("start",accessRef)', html)
        self.assertNotIn('.catch(function(){_openExam(which)', html)
        for duration in (25, 30, 35, 40):
            self.assertIn(f"min:{duration}", html)
        self.assertIn("EXD.duration_min", html)
        self.assertIn("access_ref:accessRef", ads)
        self.assertIn('fetch("/api/v3/ad/attempt"', ads)
        self.assertIn('attempt_token:String(attemptToken||"")', ads)
        self.assertIn("recordView(ad,placement,duration,accessRef,STATE.attemptToken).then(finishStart).catch(failFlow)", ads)

    def test_mistake_ad_review_uses_bound_retry_safe_authorization(self):
        html = Path("app/static/course_v3_mistakes.html").read_text(encoding="utf-8")

        self.assertIn('feature:"mistake_review"', html)
        self.assertIn('CourseAds.play("start",accessRef)', html)
        self.assertIn("access_ref:accessRef", html)
        self.assertIn("clearReviewAccessRef()", html)
        self.assertIn('fetch("/api/miniapp/mistakes/review/answer"', html)
        self.assertNotIn("q.answer_index", html)
        self.assertNotIn("q.explanation", html)
        self.assertNotIn('.catch(function(){startReview(true)', html)

    def test_course_v3_captures_lesson_mistakes_and_keeps_challenge_answer_key_private(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")

        self.assertIn("function rememberLessonMistake", html)
        self.assertIn("mistakes:(Flow.mistakes||[]).slice(0,50)", html)
        self.assertIn("correct_index:null", html)
        self.assertIn("Javob qabul qilindi", html)
        self.assertIn("Natija raund oxirida serverda tekshiriladi", html)
        self.assertIn("Результат проверит сервер в конце раунда", html)
        self.assertIn("Натиҷаро сервер дар охири раунд месанҷад", html)
        self.assertIn("Array.isArray(d.wrong_items)", html)
        self.assertIn("d.wrong_items:[]).slice(0,4)", html)
        self.assertIn("Xatolarni takrorlang", html)
        self.assertNotIn("var ans=Number(q.answer_index||0)", html)

    def test_lesson_end_ad_runs_after_celebration_only_for_free_users(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        ads = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")

        # Reklama moduli darslar sahifasiga ham ulangan.
        self.assertIn("/course_v3_data/ads.js", html)
        # Dars tugagach belgilanadi, faqat bepul + Telegram ichida.
        self.assertIn("window._pendingLessonEndAd=(!isPaidUser()&&INIT_DATA)", html)
        # Bayram/streak/reyting ekranlaridan KEYIN — closeLevelUp ichida.
        self.assertIn("if(playLessonEndAd(go))return;", html)
        self.assertIn('slot:"lesson_end"', html)
        self.assertIn('App.goPay("v3_lesson_end_ad")', html)
        # Reklama bo'lmasa yoki yiqilsa — jim o'tib xaritaga qaytadi.
        self.assertIn('CourseAds.play("end").then(go).catch(go)', html)
        # Modul slotni serverga uzatadi va dars yakunida "Davom etish" chiqadi.
        self.assertIn('"&slot="+encodeURIComponent(CFG.slot||"")', ads)
        self.assertIn('function isLessonEnd(){return CFG.slot==="lesson_end"}', ads)
        # Obuna asosiy CTA bo'lib qoladi; admin tashqi link bersa, uning alohida
        # knopkasi ham yakuniy blokda ko'rinadi.
        self.assertIn("function renderLessonEndExternal(ad)", ads)
        self.assertIn("renderLessonEndExternal(ad);", ads)
        self.assertIn('class="caa-cta ghost caa-ext"', ads)
        self.assertIn("ad.button_text", ads)
        for key in ("leLabel:", "leNote:", "leSubTitle:", "leExternal:"):
            self.assertEqual(ads.count(key), 3, f"{key} 3 tilda bo'lishi kerak")

    def test_limit_offer_keeps_reason_box_and_lesson_ad_context(self):
        html = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        ads = Path("app/static/course_v3_data/ads.js").read_text(encoding="utf-8")

        self.assertIn(".caa-ov.limit .caa-sub-t{display:none!important}", ads)
        self.assertIn(".caa-ov.limit .caa-sub-desc{display:none!important}", ads)
        self.assertIn('els.subTitle.textContent=""', ads)
        self.assertIn('els.subDesc.textContent=""', ads)
        self.assertNotIn("els.subTitle.textContent=t.limitHead", ads)
        self.assertNotIn("els.subDesc.textContent=t.limitSub", ads)

        self.assertIn("function lessonAdWhyText(l)", html)
        self.assertIn("Для этого урока подписка не обязательна", html)
        self.assertIn("CourseAds.showLimitPromo({", html)
        self.assertIn('source:"v3_lesson_ad_offer"', html)
        self.assertIn('App.goPay("v3_lesson_ad_offer")', html)

    def test_admin_can_attach_external_cta_to_lesson_end_ad(self):
        html = Path("app/static/admin.html").read_text(encoding="utf-8")

        self.assertIn('value="dars_yakuni">🎓 Dars yakuni reklamasi', html)
        self.assertIn('noBtn=t==="odiy"', html)
        self.assertIn('t==="dars_yakuni"?"Tashqi link knopkasi"', html)
        self.assertIn('t==="dars_yakuni" ? "Tashqi havola (ixtiyoriy)"', html)
        self.assertIn('fd.append("button_text",adType==="odiy"?"":', html)

    def test_desktop_installer_flow_is_direct_and_available_on_all_ad_surfaces(self):
        course = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        download = (BASE / "desktop-download.js").read_text(encoding="utf-8")
        download_css = (BASE / "desktop-download.css").read_text(encoding="utf-8")
        ads = (BASE / "ads.js").read_text(encoding="utf-8")
        landing = Path("app/static/desktop-download.html").read_text(encoding="utf-8")
        landing_js = Path("app/static/desktop-download-page.js").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("app.downloadFile(", download)
        self.assertIn('app.openLink(url)', download)
        self.assertIn("data.download_page_url || data.download_url", download)
        self.assertIn('"/api/v3/desktop-download/started"', download)
        self.assertIn('transport: transport', download)
        self.assertNotIn('showConfirm(text().mobileWarning', download)
        self.assertIn('button.dataset.pddDestinationAction = destination', download)
        self.assertIn('"share"', download)
        self.assertIn('"copy"', download)
        self.assertIn('"desktop_download_entry_seen"', download)
        self.assertIn('"desktop_download_chooser_opened"', download)
        self.assertIn('"desktop_download_destination_selected"', download)
        self.assertIn("cleanTransferUrl", download)
        self.assertNotIn("message_sent", download)
        self.assertNotIn("close_mini_app", download)
        self.assertNotIn("app.close()", download)

        self.assertIn('id="pomp-desktop-profile-root"', course)
        self.assertIn('id="ad-desktop"', course)
        self.assertIn('queuePromo("lesson_end_promo"', course)
        self.assertIn("mountAdPromoTrigger", ads)
        self.assertIn('<div class="caa-desktop" hidden></div>', ads)
        self.assertIn('var desktopPlacement=isLessonEnd()?"lesson_end_ad"', ads)
        self.assertNotIn('<button class="caa-desktop"', ads)
        self.assertLess(ads.index('caa-pay"></button>'), ads.index('caa-cont"></button>'))
        self.assertLess(
            ads.index('caa-cont"></button>'),
            ads.index('<div class="caa-desktop" hidden></div>'),
        )
        self.assertIn('var block = element("section", "pdd-ad-download")', download)
        self.assertIn("function shouldShowAdPromoEntry()", download)
        self.assertIn('state.promoReason === "already_installed"', download)
        self.assertIn('actions.classList.add("pdd-ad-download-actions")', download)
        self.assertIn('var APP_PROMO_PLATFORMS = ["macos", "windows"]', download)
        self.assertIn("buildOsButton(platform, source)", download)
        self.assertNotIn('buildOsButton("android", source)', download)
        self.assertNotIn('buildOsButton("ios", source)', download)
        self.assertIn("homePromptDailyLimitReached", download)
        self.assertIn("incrementHomePromptDailyCount", download)
        self.assertIn("platform_targets", download)
        self.assertIn("safePromoMediaUrl", download)
        self.assertIn("buildPromoMedia", download)
        self.assertIn("pdd-ad-download-media", download)
        self.assertNotIn('element("button", "pdd-ad-trigger")', download)
        self.assertIn('prepareTransfer(destination, platform, data.transfer_url)', download)
        self.assertLess(
            download.index("fetch(REQUEST_ENDPOINT, requestOptions)"),
            download.index("prepareTransfer(destination, platform, data.transfer_url)"),
        )
        self.assertIn('z-index: 9101', download_css)
        self.assertIn('z-index: 9102', download_css)
        self.assertIn("z-index:9000", ads)
        self.assertIn('href="/desktop-download-page.css', landing)
        self.assertIn('src="/desktop-download-page.js', landing)
        self.assertIn('src="/assets/hsk-ai-avatar.webp"', landing)
        self.assertIn('seal.src = "/assets/hsk-ai-avatar.webp"', download)
        self.assertIn('logo.src = "/assets/hsk-ai-avatar.webp"', download)
        self.assertIn('buildProductPreview("card")', download)
        self.assertIn('buildProductPreview("modal")', download)
        self.assertNotIn('element("span", "pdd-seal", "桌")', download)
        self.assertNotIn('element("span", "pdd-laptop-seal", "桌")', download)
        self.assertNotIn("<script>", landing)
        self.assertIn('"/api/v3/desktop-download/public-status"', landing_js)
        self.assertIn('url.searchParams.set("request", token)', landing_js)

        for page in (
            "course_v3_memorize.html",
            "course_v3_mistakes.html",
            "course_v3_pronunciation.html",
            "course_v3_recognition.html",
            "course_v3_test.html",
        ):
            html = Path("app/static", page).read_text(encoding="utf-8")
            self.assertIn(
                "/course_v3_data/desktop-download.css?v=20260812-2", html, page
            )
            self.assertIn(
                "/course_v3_data/desktop-download.js?v=20260812-2", html, page
            )
            self.assertIn("/course_v3_data/ads.js?v=20260812-2", html, page)

    def test_desktop_profile_card_is_early_clear_and_deep_linkable(self):
        course = Path("app/static/course-v3.html").read_text(encoding="utf-8")
        download = (BASE / "desktop-download.js").read_text(encoding="utf-8")

        goal_position = course.index("+'<div class=\"pgoal\"")
        desktop_position = course.index(
            "+'<div id=\"pomp-desktop-profile-root\"></div>'"
        )
        calendar_position = course.index("p.calTitle", desktop_position)
        self.assertLess(goal_position, desktop_position)
        self.assertLess(desktop_position, calendar_position)

        self.assertEqual(download.count("mobileCardHint:"), 3)
        self.assertEqual(download.count("previewTranslation:"), 3)
        self.assertIn('main.appendChild(buildProductPreview("card"))', download)
        self.assertIn("main.appendChild(buildBenefits(true))", download)
        self.assertIn("copy.macUnavailable", download)
        self.assertIn("copy.windowsUnavailable", download)
        self.assertIn("if (isDesktop || !state.availabilityLoaded)", download)

        self.assertIn(
            'params.get("desktop_download") === "1"', download
        )
        self.assertIn('card.classList.add("pdd-card-focus")', download)
        self.assertIn("card.focus({ preventScroll: true })", download)
        self.assertIn("card.scrollIntoView({", download)
        self.assertEqual(download.count("availabilityError:"), 4)
        self.assertEqual(download.count("retryStatus:"), 3)
        self.assertIn('state.availabilityError ? " is-error" : ""', download)
        self.assertIn("loadAvailability();", download)

    def test_admin_has_app_promo_controls(self):
        html = Path("app/static/admin.html").read_text(encoding="utf-8")
        main = Path("app/main.py").read_text(encoding="utf-8")
        service = Path("app/services/desktop_app_promo_settings_service.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("App reklamasi", html)
        self.assertIn('appPromoChipHtml("platform","macos","MacBook"', html)
        self.assertIn('appPromoChipHtml("platform","windows","Windows"', html)
        self.assertNotIn('appPromoChipHtml("platform","android","Android"', html)
        self.assertNotIn('appPromoChipHtml("platform","ios","Apple"', html)
        self.assertIn("data-app-promo-media-upload", html)
        self.assertIn("/api/admin-miniapp/desktop-promo/media", html)
        self.assertIn("/api/admin-miniapp/desktop-promo/save", html)
        self.assertIn("/uploads/app_promo/", main)
        self.assertIn("desktop_app_promo", main)
        self.assertIn("daily_limit=3", service)
        self.assertIn('"android": False', service)
        self.assertIn('"ios": False', service)


if __name__ == "__main__":
    unittest.main()
