import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.bot.handlers.course import (
    _MessageEditResponder as CourseMessageEditResponder,
    _send_course_miniapp_entry_block,
    _show_required_channel_for_pending_action,
)
from app.bot.handlers.required_channel import force_sub_check
from app.bot.keyboards.course import (
    course_dialogue_keyboard,
    course_grammar_keyboard,
    course_homework_keyboard,
    course_intro_keyboard,
    course_next_step_keyboard,
    lesson_selection_keyboard,
    reminder_time_keyboard,
    review_choice_keyboard,
)
from app.bot.keyboards.course_miniapp import (
    course_study_miniapp_keyboard,
    course_v3_miniapp_keyboard,
)
from app.bot.keyboards.onboarding import (
    course_mode_entry_keyboard,
    daily_practice_check_keyboard,
    daily_practice_finish_keyboard,
    language_keyboard,
    trial_lesson_selection_keyboard,
)
from app.bot.middlewares.required_channel import (
    FORCE_SUB_ACTION_OPEN_COURSE,
    FORCE_SUB_ACTION_OPEN_FREE_QA,
    PENDING_FORCE_SUB_ACTION,
    PENDING_FORCE_SUB_PAYLOAD,
)
from app.services.course_miniapp_onboarding_service import CourseMiniAppOnboardingService
from app.services.course_miniapp_profile_service import CourseMiniAppProfileService


class CourseModeEntryKeyboardTests(unittest.TestCase):
    def test_course_mode_buttons_keep_copy_and_force_sub_callbacks(self):
        expected = {
            "uz": ("🚀 Kursni boshlash", "🤖 Oddiy rejim (chatda savol-javob)"),
            "ru": ("🚀 Начать курс", "🤖 Обычный режим (вопрос-ответ в чате)"),
            "tj": ("🚀 Оғози курс", "🤖 Реҷаи оддӣ (савол-ҷавоб дар чат)"),
        }
        for language, labels in expected.items():
            with self.subTest(language=language):
                keyboard = course_mode_entry_keyboard(language)
                course_button = keyboard.inline_keyboard[0][0]
                qa_button = keyboard.inline_keyboard[1][0]

                self.assertEqual((course_button.text, qa_button.text), labels)
                self.assertEqual(course_button.callback_data, "mode:course")
                self.assertIsNone(course_button.web_app)
                self.assertEqual(qa_button.callback_data, "mode:free_qa")

    def test_language_keyboard_uses_shared_labels_and_keeps_callbacks(self):
        buttons = language_keyboard().inline_keyboard[0]

        self.assertEqual(
            [button.text for button in buttons],
            ["🇹🇯 Тоҷикӣ", "🇷🇺 Русский", "🇺🇿 O'zbek"],
        )
        self.assertEqual(
            [button.callback_data for button in buttons],
            ["lang:tj", "lang:ru", "lang:uz"],
        )

    def test_daily_practice_buttons_keep_copy_and_callbacks(self):
        expected = {
            "uz": (
                ("📚 Kursni boshlash", "daily_practice:course"),
                ("💬 Bepul savol-javobga o'tish", "mode:free_qa"),
                ("✅ Javoblarni ko'rish", "daily_practice:complete"),
            ),
            "ru": (
                ("📚 Начать курс", "daily_practice:course"),
                ("💬 Перейти в бесплатный вопрос-ответ", "mode:free_qa"),
                ("✅ Посмотреть ответы", "daily_practice:complete"),
            ),
            "tj": (
                ("📚 Оғози курс", "daily_practice:course"),
                ("💬 Ба савол-ҷавоби ройгон гузаштан", "mode:free_qa"),
                ("✅ Дидани ҷавобҳо", "daily_practice:complete"),
            ),
        }
        for language, buttons in expected.items():
            with self.subTest(language=language):
                finish = daily_practice_finish_keyboard(language)
                check = daily_practice_check_keyboard(language)
                actual = (
                    (finish.inline_keyboard[0][0].text,
                     finish.inline_keyboard[0][0].callback_data),
                    (finish.inline_keyboard[1][0].text,
                     finish.inline_keyboard[1][0].callback_data),
                    (check.inline_keyboard[0][0].text,
                     check.inline_keyboard[0][0].callback_data),
                )
                self.assertEqual(actual, buttons)

    def test_trial_lesson_pagination_keeps_localized_labels_and_callbacks(self):
        lessons = [
            SimpleNamespace(id=index, lesson_order=index + 1, title="{}")
            for index in range(8)
        ]
        expected = {
            "uz": ("Keyingi ➡️", "⬅️ Oldingi"),
            "ru": ("Далее ➡️", "⬅️ Назад"),
            "tj": ("Баъд ➡️", "⬅️ Қабл"),
        }
        for language, (next_label, previous_label) in expected.items():
            with self.subTest(language=language):
                next_keyboard = trial_lesson_selection_keyboard(
                    lessons, page=0, lang=language
                )
                previous_keyboard = trial_lesson_selection_keyboard(
                    lessons, page=1, lang=language
                )
                next_button = next_keyboard.inline_keyboard[-1][0]
                previous_button = previous_keyboard.inline_keyboard[-1][0]
                self.assertEqual((next_button.text, next_button.callback_data),
                                 (next_label, "trial_lesson:page:1"))
                self.assertEqual((previous_button.text, previous_button.callback_data),
                                 (previous_label, "trial_lesson:page:0"))

    def test_trial_lesson_pagination_keeps_unknown_locale_arrow_fallback(self):
        lessons = [
            SimpleNamespace(id=index, lesson_order=index + 1, title="{}")
            for index in range(8)
        ]
        next_keyboard = trial_lesson_selection_keyboard(
            lessons, page=0, lang="unknown"
        )
        previous_keyboard = trial_lesson_selection_keyboard(
            lessons, page=1, lang="unknown"
        )

        self.assertEqual(next_keyboard.inline_keyboard[-1][0].text, "➡️")
        self.assertEqual(previous_keyboard.inline_keyboard[-1][0].text, "⬅️")


class CourseKeyboardLocalizationTests(unittest.TestCase):
    def test_course_keyboard_labels_and_callbacks_match_all_locales(self):
        expected = {
            "uz": {
                "miniapp": "📚 Mini Appda ochish",
                "intro": ("📖 So'zlarni o'rganamiz", "course:go_vocab"),
                "dialogue": ("📐 Grammatikaga o'tamiz", "course:go_grammar"),
                "grammar": ("✏️ Mashqlarga o'tamiz", "course:go_exercise"),
                "homework": ("✅ Dars tugadi — Keyingi darsga", "course:start_next_lesson"),
                "continue": ("▶️ Davom etamiz", "course:go_next_step"),
                "review": (("✅ Ha, takrorlaymiz", "course:review_yes"), ("➡️ Yo'q, keyingisiga", "course:review_no")),
                "cancel": ("❌ Bekor qilish", "course:reminder_cancel"),
                "v3": "📚 Kursni ochish",
                "study": "📚 Kursni Mini Appda ochish",
            },
            "ru": {
                "miniapp": "📚 Открыть в Mini App",
                "intro": ("📖 Изучаем слова", "course:go_vocab"),
                "dialogue": ("📐 Переходим к грамматике", "course:go_grammar"),
                "grammar": ("✏️ Переходим к упражнениям", "course:go_exercise"),
                "homework": ("✅ Урок завершён — К следующему уроку", "course:start_next_lesson"),
                "continue": ("▶️ Продолжаем", "course:go_next_step"),
                "review": (("✅ Да, повторим", "course:review_yes"), ("➡️ Нет, к следующему", "course:review_no")),
                "cancel": ("❌ Отмена", "course:reminder_cancel"),
                "v3": "📚 Открыть курс",
                "study": "📚 Открыть курс в Mini App",
            },
            "tj": {
                "miniapp": "📚 Дар Mini App кушодан",
                "intro": ("📖 Калимаҳоро меомӯзем", "course:go_vocab"),
                "dialogue": ("📐 Ба грамматика мегузарем", "course:go_grammar"),
                "grammar": ("✏️ Ба машқҳо мегузарем", "course:go_exercise"),
                "homework": ("✅ Дарс тамом шуд — Ба дарси навбатӣ", "course:start_next_lesson"),
                "continue": ("▶️ Идома медиҳем", "course:go_next_step"),
                "review": (("✅ Бале, такрор мекунем", "course:review_yes"), ("➡️ Не, ба навбатӣ", "course:review_no")),
                "cancel": ("❌ Бекор кардан", "course:reminder_cancel"),
                "v3": "📚 Курсро кушодан",
                "study": "📚 Курсро дар Mini App кушодан",
            },
        }
        lessons = [
            SimpleNamespace(id=index, level="hsk1", lesson_order=index + 1, title="{}")
            for index in range(8)
        ]
        for language, labels in expected.items():
            with self.subTest(language=language):
                miniapp = course_intro_keyboard(language).inline_keyboard[-1][0]
                self.assertEqual(miniapp.text, labels["miniapp"])

                intro = course_intro_keyboard(language).inline_keyboard[0][0]
                dialogue = course_dialogue_keyboard(language).inline_keyboard[0][1]
                grammar = course_grammar_keyboard(language).inline_keyboard[0][0]
                homework = course_homework_keyboard(language).inline_keyboard[0][0]
                next_step = course_next_step_keyboard(language).inline_keyboard[0][0]
                review = review_choice_keyboard(language).inline_keyboard[0]
                cancel = reminder_time_keyboard(language).inline_keyboard[1][0]
                self.assertEqual((intro.text, intro.callback_data), labels["intro"])
                self.assertEqual((dialogue.text, dialogue.callback_data), labels["dialogue"])
                self.assertEqual((grammar.text, grammar.callback_data), labels["grammar"])
                self.assertEqual((homework.text, homework.callback_data), labels["homework"])
                self.assertEqual((next_step.text, next_step.callback_data), labels["continue"])
                self.assertEqual(
                    tuple((button.text, button.callback_data) for button in review),
                    labels["review"],
                )
                self.assertEqual((cancel.text, cancel.callback_data), labels["cancel"])

                v3 = course_v3_miniapp_keyboard(language).inline_keyboard[0][0]
                study = course_study_miniapp_keyboard(language).inline_keyboard[0][0]
                self.assertEqual(v3.text, labels["v3"])
                self.assertEqual(study.text, labels["study"])

                next_page = lesson_selection_keyboard(lessons, page=0, lang=language).inline_keyboard[-1][0]
                previous_page = lesson_selection_keyboard(lessons, page=1, lang=language).inline_keyboard[-1][0]
                self.assertEqual((next_page.text, next_page.callback_data),
                                 ({"uz": "Keyingi ➡️", "ru": "Далее ➡️", "tj": "Баъд ➡️"}[language], "course:lessons_page:1"))
                self.assertEqual((previous_page.text, previous_page.callback_data),
                                 ({"uz": "⬅️ Oldingi", "ru": "⬅️ Назад", "tj": "⬅️ Қабл"}[language], "course:lessons_page:0"))

    def test_course_pagination_preserves_unknown_locale_arrow_fallback(self):
        lessons = [
            SimpleNamespace(id=index, level="hsk1", lesson_order=index + 1, title="{}")
            for index in range(8)
        ]
        next_page = lesson_selection_keyboard(lessons, page=0, lang="unknown").inline_keyboard[-1][0]
        previous_page = lesson_selection_keyboard(lessons, page=1, lang="unknown").inline_keyboard[-1][0]
        self.assertEqual(next_page.text, "➡️")
        self.assertEqual(previous_page.text, "⬅️")


class _CourseEntryMessage:
    def __init__(self, *, photo_error: Exception | None = None):
        self.answer_mock = AsyncMock()
        self.answer_photo_mock = AsyncMock(side_effect=photo_error)
        self.delete_mock = AsyncMock()
        self.edit_text_mock = AsyncMock()

    async def answer(self, text: str, **kwargs):
        return await self.answer_mock(text, **kwargs)

    async def answer_photo(self, photo, **kwargs):
        return await self.answer_photo_mock(photo=photo, **kwargs)

    async def delete(self):
        return await self.delete_mock()

    async def edit_text(self, text: str, **kwargs):
        return await self.edit_text_mock(text, **kwargs)


class CourseMiniAppEntryMediaTests(unittest.IsolatedAsyncioTestCase):
    async def test_course_entry_uses_localized_photo_with_text_as_caption(self):
        message = _CourseEntryMessage()

        await _send_course_miniapp_entry_block(
            respond=message.answer,
            lang="uz",
            text="<b>Kurs</b>",
            keyboard="keyboard",
        )

        message.answer_photo_mock.assert_awaited_once()
        kwargs = message.answer_photo_mock.await_args.kwargs
        self.assertTrue(str(kwargs["photo"].path).endswith("course_promo/uz.jpg"))
        self.assertEqual(kwargs["caption"], "<b>Kurs</b>")
        self.assertEqual(kwargs["reply_markup"], "keyboard")
        self.assertEqual(kwargs["parse_mode"], "HTML")
        message.answer_mock.assert_not_awaited()

    async def test_course_entry_falls_back_to_text_when_photo_send_fails(self):
        message = _CourseEntryMessage(photo_error=RuntimeError("send failed"))

        await _send_course_miniapp_entry_block(
            respond=message.answer,
            lang="ru",
            text="<b>Курс</b>",
            keyboard="keyboard",
        )

        message.answer_photo_mock.assert_awaited_once()
        message.answer_mock.assert_awaited_once_with(
            "<b>Курс</b>",
            reply_markup="keyboard",
            parse_mode="HTML",
        )

    async def test_edit_responder_replaces_old_text_block_with_photo(self):
        message = _CourseEntryMessage()
        respond = CourseMessageEditResponder(message)

        await _send_course_miniapp_entry_block(
            respond=respond,
            lang="tj",
            text="<b>Курс</b>",
            keyboard="keyboard",
        )

        message.delete_mock.assert_awaited_once()
        message.answer_photo_mock.assert_awaited_once()
        message.edit_text_mock.assert_not_awaited()


class _FakeForceSubState:
    def __init__(self, data):
        self.data = dict(data)

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **values):
        self.data.update(values)


class RequiredChannelResumeTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _callback():
        return SimpleNamespace(
            from_user=SimpleNamespace(id=123),
            bot=SimpleNamespace(),
            answer=AsyncMock(),
            message=SimpleNamespace(
                message_id=10,
                delete=AsyncMock(),
                answer=AsyncMock(),
            ),
        )

    async def test_force_sub_check_resumes_pending_course_mode(self):
        callback = self._callback()
        state = _FakeForceSubState(
            {
                PENDING_FORCE_SUB_ACTION: FORCE_SUB_ACTION_OPEN_COURSE,
                PENDING_FORCE_SUB_PAYLOAD: {"source": "mode_course"},
            }
        )
        session = SimpleNamespace(flush=AsyncMock())
        user = SimpleNamespace(language="uz", last_active_at=None)

        with (
            patch("app.bot.handlers.required_channel.UserRepository") as user_repo_class,
            patch("app.bot.handlers.required_channel.RequiredChannelService") as service_class,
            patch("app.bot.handlers.course.send_course_miniapp_entry", new=AsyncMock()) as send_entry,
        ):
            user_repo_class.return_value.get_by_telegram_id = AsyncMock(return_value=user)
            service_class.return_value.missing_channels = AsyncMock(return_value=[])

            await force_sub_check(callback, state, session)

        send_entry.assert_awaited_once()
        kwargs = send_entry.await_args.kwargs
        self.assertEqual(kwargs["telegram_id"], 123)
        self.assertEqual(kwargs["source"], "mode_course")
        self.assertIsNone(state.data[PENDING_FORCE_SUB_ACTION])
        self.assertIsNone(state.data[PENDING_FORCE_SUB_PAYLOAD])

    async def test_force_sub_check_resumes_pending_free_qa_mode(self):
        callback = self._callback()
        state = _FakeForceSubState(
            {
                PENDING_FORCE_SUB_ACTION: FORCE_SUB_ACTION_OPEN_FREE_QA,
                PENDING_FORCE_SUB_PAYLOAD: {"source": "mode_free_qa"},
            }
        )
        session = SimpleNamespace(flush=AsyncMock())
        user = SimpleNamespace(language="uz", last_active_at=None)

        with (
            patch("app.bot.handlers.required_channel.UserRepository") as user_repo_class,
            patch("app.bot.handlers.required_channel.RequiredChannelService") as service_class,
            patch("app.bot.handlers.course.show_free_qa_level_choice", new=AsyncMock()) as show_level,
        ):
            user_repo_class.return_value.get_by_telegram_id = AsyncMock(return_value=user)
            service_class.return_value.missing_channels = AsyncMock(return_value=[])

            await force_sub_check(callback, state, session)

        show_level.assert_awaited_once()
        kwargs = show_level.await_args.kwargs
        self.assertEqual(kwargs["lang"], "uz")
        self.assertIsNone(state.data[PENDING_FORCE_SUB_ACTION])
        self.assertIsNone(state.data[PENDING_FORCE_SUB_PAYLOAD])


class RequiredChannelPromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_pending_mode_required_channels_edit_current_message(self):
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=123),
            bot=SimpleNamespace(),
            answer=AsyncMock(),
            message=SimpleNamespace(
                message_id=10,
                edit_text=AsyncMock(),
                answer=AsyncMock(),
            ),
        )
        state = _FakeForceSubState({})
        session = SimpleNamespace(commit=AsyncMock(), flush=AsyncMock())
        user = SimpleNamespace(force_sub_required_at=None)

        with patch("app.bot.handlers.course.RequiredChannelService") as service_class:
            service = service_class.return_value
            service.missing_channels = AsyncMock(return_value=[SimpleNamespace()])
            service.build_required_text.return_value = "join channels"
            service.build_required_keyboard.return_value = None

            blocked = await _show_required_channel_for_pending_action(
                callback=callback,
                state=state,
                session=session,
                user=user,
                lang="uz",
                action=FORCE_SUB_ACTION_OPEN_COURSE,
                payload={"source": "mode_course"},
            )

        self.assertTrue(blocked)
        callback.message.edit_text.assert_awaited_once()
        callback.message.answer.assert_not_awaited()
        self.assertEqual(state.data[PENDING_FORCE_SUB_ACTION], FORCE_SUB_ACTION_OPEN_COURSE)


class CourseMiniAppOnboardingValidationTests(unittest.TestCase):
    def test_levels_are_normalized_without_inventing_content_levels(self):
        self.assertEqual(CourseMiniAppOnboardingService.normalize_level("Beginner"), "beginner")
        self.assertEqual(CourseMiniAppOnboardingService.content_level("beginner"), "hsk1")
        self.assertEqual(CourseMiniAppOnboardingService.render_level("hsk4", 12), "hsk4b")
        with self.assertRaises(ValueError):
            CourseMiniAppOnboardingService.normalize_level("hsk5")

    def test_foundation_is_required_only_for_beginner_first_start(self):
        requires = CourseMiniAppOnboardingService.requires_foundation
        self.assertTrue(
            requires(
                level="beginner",
                start_mode="lesson_1",
                onboarding_completed=False,
                review_only=False,
            )
        )
        self.assertFalse(
            requires(
                level="hsk1",
                start_mode="lesson_1",
                onboarding_completed=False,
                review_only=False,
            )
        )
        self.assertFalse(
            requires(
                level="beginner",
                start_mode="lesson_1",
                onboarding_completed=True,
                review_only=False,
            )
        )
        self.assertFalse(
            requires(
                level="beginner",
                start_mode="placement",
                onboarding_completed=False,
                review_only=False,
            )
        )


class CourseMiniAppOnboardingFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_level_does_not_depend_on_hsk30_flag_lookup(self):
        service = CourseMiniAppOnboardingService(SimpleNamespace())
        with patch(
            "app.services.course_miniapp_onboarding_service.Hsk30FeatureService.is_enabled",
            new=AsyncMock(side_effect=RuntimeError("settings unavailable")),
        ) as enabled:
            self.assertEqual(await service._normalize_request_level("Beginner"), "beginner")
        enabled.assert_not_awaited()

    async def test_hsk30_level_still_requires_enabled_flag(self):
        service = CourseMiniAppOnboardingService(SimpleNamespace())
        with patch(
            "app.services.course_miniapp_onboarding_service.Hsk30FeatureService.is_enabled",
            new=AsyncMock(return_value=False),
        ):
            with self.assertRaises(ValueError):
                await service._normalize_request_level("nhsk1")
        with patch(
            "app.services.course_miniapp_onboarding_service.Hsk30FeatureService.is_enabled",
            new=AsyncMock(return_value=True),
        ):
            self.assertEqual(await service._normalize_request_level("nhsk1"), "nhsk1")

    @staticmethod
    def _profile():
        return SimpleNamespace(
            id=7,
            goal="hsk_exam",
            daily_minutes=10,
            start_mode="continue",
            timezone_offset_minutes=0,
            onboarding_completed_at=None,
        )

    @staticmethod
    async def _save_profile(profile, **values):
        profile.goal = values["goal"]
        profile.daily_minutes = values["daily_minutes"]
        profile.start_mode = values["start_mode"]
        profile.timezone_offset_minutes = values["timezone_offset_minutes"]
        if values["complete_onboarding"]:
            profile.onboarding_completed_at = datetime.now(timezone.utc)
        return profile

    async def test_new_user_gets_first_lesson_without_payment_changes(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = CourseMiniAppOnboardingService(session)
        user = SimpleNamespace(
            id=4,
            telegram_id=123,
            level="beginner",
            learning_mode="qa",
            voice_mode="none",
            status="trial",
            payment_status="none",
            trial_course_lesson_id=None,
            trial_course_started_at=None,
        )
        profile = self._profile()
        progress = SimpleNamespace(level="beginner", current_lesson_id=None)
        lesson = SimpleNamespace(id=10, lesson_order=1, level="hsk1")

        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.profile_service = SimpleNamespace(
            validate_preferences=CourseMiniAppProfileService.validate_preferences,
            get_or_create=AsyncMock(return_value=profile),
            save_preferences=AsyncMock(side_effect=self._save_profile),
        )
        service.engine = SimpleNamespace(
            progress_repo=SimpleNamespace(
                get_by_user_id=AsyncMock(return_value=None),
                create=AsyncMock(return_value=progress),
                set_current_lesson_and_step=AsyncMock(),
            ),
            lesson_repo=SimpleNamespace(
                get_by_id=AsyncMock(return_value=None),
                get_first_by_level=AsyncMock(return_value=lesson),
            ),
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))

        with (
            patch(
                "app.services.course_miniapp_onboarding_service.CourseTrialService"
            ) as trial_class,
            patch(
                "app.services.course_miniapp_onboarding_service.CourseMiniAppAnalyticsService",
                return_value=analytics,
            ),
        ):
            # Onboarding faqat BELGILAB qo'yadi: boshlash nuqtasini tanlash
            # kunlik bepul dars chegarasini sarflamasligi kerak.
            trial_class.return_value.mark_trial_lesson = AsyncMock(return_value=None)
            trial_class.return_value.ensure_trial_lesson = AsyncMock(return_value=True)
            result = await service.complete(
                123,
                level="beginner",
                goal="hsk_exam",
                daily_minutes=10,
                start_mode="lesson_1",
                timezone_offset_minutes=300,
                activation_variant="direct_start_v1",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["level"], "hsk1")
        self.assertEqual(result["lesson"], 1)
        self.assertTrue(result["foundation_required"])
        self.assertEqual(user.learning_mode, "course")
        self.assertEqual(user.payment_status, "none")
        service.engine.progress_repo.set_current_lesson_and_step.assert_awaited_once()
        trial_class.return_value.mark_trial_lesson.assert_awaited_once()
        trial_class.return_value.ensure_trial_lesson.assert_not_awaited()
        self.assertEqual(analytics.record_server_event.await_count, 5)
        completed_call = next(
            call
            for call in analytics.record_server_event.await_args_list
            if call.kwargs["event_name"] == "onboarding_completed"
        )
        self.assertEqual(
            completed_call.kwargs["payload"]["activation_variant"],
            "direct_start_v1",
        )

    async def test_cross_level_lesson_one_does_not_reset_existing_progress(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = CourseMiniAppOnboardingService(session)
        user = SimpleNamespace(id=4, telegram_id=123, level="hsk2")
        profile = self._profile()
        progress = SimpleNamespace(level="hsk2", current_lesson_id=20)
        lesson = SimpleNamespace(id=20, lesson_order=4, level="hsk2")

        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.profile_service = SimpleNamespace(
            validate_preferences=CourseMiniAppProfileService.validate_preferences,
            get_or_create=AsyncMock(return_value=profile),
        )
        service.engine = SimpleNamespace(
            progress_repo=SimpleNamespace(get_by_user_id=AsyncMock(return_value=progress)),
            lesson_repo=SimpleNamespace(get_by_id=AsyncMock(return_value=lesson)),
        )

        result = await service.complete(
            123,
            level="hsk1",
            goal="hsk_exam",
            daily_minutes=10,
            start_mode="lesson_1",
        )

        self.assertEqual(result, {"ok": False, "error": "course_level_change_requires_placement"})
        session.commit.assert_not_awaited()

    async def test_beginner_entry_level_is_saved_when_hsk1_first_lesson_already_exists(self):
        session = SimpleNamespace(commit=AsyncMock())
        service = CourseMiniAppOnboardingService(session)
        user = SimpleNamespace(
            id=4,
            telegram_id=123,
            level="hsk1",
            learning_mode="qa",
            voice_mode="none",
        )
        profile = self._profile()
        lesson = SimpleNamespace(id=10, lesson_order=1, level="hsk1")
        progress = SimpleNamespace(level="hsk1", current_lesson_id=lesson.id)

        service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        service.profile_service = SimpleNamespace(
            validate_preferences=CourseMiniAppProfileService.validate_preferences,
            get_or_create=AsyncMock(return_value=profile),
            save_preferences=AsyncMock(side_effect=self._save_profile),
        )
        service.engine = SimpleNamespace(
            progress_repo=SimpleNamespace(get_by_user_id=AsyncMock(return_value=progress)),
            lesson_repo=SimpleNamespace(
                get_by_id=AsyncMock(return_value=lesson),
                get_first_by_level=AsyncMock(return_value=lesson),
            ),
        )
        analytics = SimpleNamespace(record_server_event=AsyncMock(return_value={"ok": True}))

        with patch(
            "app.services.course_miniapp_onboarding_service.CourseMiniAppAnalyticsService",
            return_value=analytics,
        ):
            result = await service.complete(
                123,
                level="beginner",
                goal="hsk_exam",
                daily_minutes=10,
                start_mode="lesson_1",
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["foundation_required"])
        self.assertFalse(result["review_only"])
        self.assertEqual(user.level, "beginner")


if __name__ == "__main__":
    unittest.main()
