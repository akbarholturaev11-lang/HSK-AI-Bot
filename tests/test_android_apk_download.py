"""The APK the bot hands out.

Distribution is this chat and nothing else — no Play listing, no download
page — so everything that can strand a learner happens here:

* A build that installs and then traps whoever installed it. The `play`
  flavour compiles out every external checkout, so that learner could never
  pay; a `debug` build carries the `.debug` application id, so no real release
  can ever update it. Both look perfectly healthy on the admin's own phone.
* A published row that is missing its `file_id`. `current()` must read that as
  "nothing to give" rather than hand a learner an intro with no file under it.
* A `file_id` that has stopped resolving. The learner must be told, not left
  waiting, and the send must not be counted as a delivery.
"""

import unittest
import unittest.mock
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.course_miniapp_event import (
    COURSE_MINIAPP_EVENT_NAMES,
    CourseMiniAppEvent,
)
from app.db.models.user import User
from app.bot.utils.i18n import TEXTS
from app.services.android_release_service import (
    ANDROID_RELEASE_KEY,
    MAX_APK_BYTES,
    AndroidRelease,
    AndroidReleaseError,
    AndroidReleaseService,
    format_size,
    parse_artifact_name,
    parse_version_text,
)


RELEASE_APK = "hsk-ai-1.1.0-2-direct-release.apk"


class ArtifactNameTests(unittest.TestCase):
    def test_a_gradle_release_name_carries_its_version(self):
        artifact = parse_artifact_name(RELEASE_APK)
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.version_name, "1.1.0")
        self.assertEqual(artifact.version_code, 2)
        self.assertEqual(artifact.flavor, "direct")
        self.assertEqual(artifact.build_type, "release")
        self.assertTrue(artifact.is_distributable)

    def test_the_play_build_is_not_handed_out_from_the_bot(self):
        artifact = parse_artifact_name("hsk-ai-1.1.0-2-play-release.apk")
        self.assertIsNotNone(artifact)
        self.assertFalse(artifact.is_distributable)

    def test_a_debug_build_is_not_handed_out_either(self):
        artifact = parse_artifact_name("hsk-ai-1.1.0-2-direct-debug.apk")
        self.assertIsNotNone(artifact)
        self.assertFalse(artifact.is_distributable)

    def test_an_unrecognised_name_yields_nothing_rather_than_a_guess(self):
        for name in ("app-direct-release.apk", "hsk-ai.apk", "", "hsk-ai-1.1.0-direct-release.apk"):
            with self.subTest(name=name):
                self.assertIsNone(parse_artifact_name(name))


class VersionTextTests(unittest.TestCase):
    def test_the_shapes_an_admin_actually_types(self):
        self.assertEqual(parse_version_text("1.2.0"), ("1.2.0", None))
        self.assertEqual(parse_version_text("1.2.0 3"), ("1.2.0", 3))
        self.assertEqual(parse_version_text("1.2.0 (3)"), ("1.2.0", 3))
        self.assertEqual(parse_version_text("  2.0  "), ("2.0", None))
        self.assertEqual(parse_version_text("1.2.0-rc1"), ("1.2.0-rc1", None))

    def test_junk_is_refused_instead_of_becoming_a_version(self):
        for text in ("", "keyinroq", "v", "1.2.0 abc"):
            with self.subTest(text=text):
                with self.assertRaises(AndroidReleaseError):
                    parse_version_text(text)


class SizeTextTests(unittest.TestCase):
    def test_sizes_read_the_way_a_person_reads_them(self):
        self.assertEqual(format_size(3_766_687), "3.6 MB")
        self.assertEqual(format_size(4096), "4 KB")
        self.assertEqual(format_size(12), "12 B")
        self.assertEqual(format_size(0), "0 B")


class StoredReleaseTests(unittest.TestCase):
    def test_a_release_survives_the_round_trip_through_settings(self):
        original = AndroidRelease(
            file_id="BQACAgIAAx",
            file_unique_id="AgAD1",
            file_name=RELEASE_APK,
            file_size=3_766_687,
            version_name="1.1.0",
            version_code=2,
            published_at=__import__("datetime").datetime(
                2026, 9, 15, 12, 36, tzinfo=__import__("datetime").timezone.utc
            ),
            published_by=7965751363,
        )
        restored = AndroidRelease.from_json(original.to_json())
        self.assertEqual(restored, original)
        self.assertEqual(restored.version_text, "1.1.0 (2)")
        self.assertEqual(restored.size_text, "3.6 MB")

    def test_a_release_without_a_version_code_still_reads_cleanly(self):
        release = AndroidRelease.from_json(
            '{"file_id":"X","version_name":"1.1.0","file_size":10}'
        )
        self.assertEqual(release.version_text, "1.1.0")

    def test_a_row_with_no_file_id_is_nothing_to_give(self):
        for raw in ('{"version_name":"1.1.0"}', "{}", "not json", ""):
            with self.subTest(raw=raw):
                self.assertIsNone(AndroidRelease.from_json(raw))


class FakeBot:
    def __init__(self, *, document_fails: bool = False):
        self.messages: list[tuple[int, str]] = []
        self.documents: list[tuple[int, str, str]] = []
        self.document_fails = document_fails

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append((chat_id, text))

    async def send_document(self, chat_id, file_id, caption=None, **kwargs):
        if self.document_fails:
            raise RuntimeError("wrong file identifier/HTTP URL specified")
        self.documents.append((chat_id, file_id, caption or ""))


class DatabaseBackedTest(unittest.IsolatedAsyncioTestCase):
    TELEGRAM_ID = 5150
    CHAT_ID = 5150

    async def asyncSetUp(self):
        self.db = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.db.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.db.dispose()

    async def _add_user(self, session, language: str = "uz") -> User:
        user = User(telegram_id=self.TELEGRAM_ID, language=language)
        session.add(user)
        await session.commit()
        return user

    async def _publish(self, session, **overrides) -> AndroidRelease:
        payload = {
            "file_id": "BQACAgIAAx",
            "file_unique_id": "AgAD1",
            "file_name": RELEASE_APK,
            "file_size": 3_766_687,
            "version_name": "1.1.0",
            "version_code": 2,
            "published_by": 7965751363,
        }
        payload.update(overrides)
        return await AndroidReleaseService(session).publish(**payload)

    async def _event_names(self, session) -> list[str]:
        rows = await session.execute(select(CourseMiniAppEvent.event_name))
        return list(rows.scalars())


class PublishingTests(DatabaseBackedTest):
    async def test_publishing_then_reading_back_gives_the_same_release(self):
        async with self.sessions() as session:
            published = await self._publish(session)
            current = await AndroidReleaseService(session).current()
            self.assertEqual(current.file_id, published.file_id)
            self.assertEqual(current.version_text, "1.1.0 (2)")

    async def test_withdrawing_leaves_nothing_to_hand_out(self):
        async with self.sessions() as session:
            await self._publish(session)
            await AndroidReleaseService(session).withdraw()
            self.assertIsNone(await AndroidReleaseService(session).current())

    async def test_a_file_telegram_could_never_send_is_refused_at_upload(self):
        async with self.sessions() as session:
            with self.assertRaises(AndroidReleaseError):
                await self._publish(session, file_size=MAX_APK_BYTES + 1)
            # Nothing was stored, so a learner is not offered a file that
            # would fail on every single send.
            self.assertIsNone(await AndroidReleaseService(session).current())

    async def test_an_empty_file_is_refused(self):
        async with self.sessions() as session:
            with self.assertRaises(AndroidReleaseError):
                await self._publish(session, file_size=0)

    async def test_a_release_with_no_version_is_refused(self):
        async with self.sessions() as session:
            with self.assertRaises(AndroidReleaseError):
                await self._publish(session, version_name="  ")

    async def test_publishing_again_replaces_the_previous_release(self):
        async with self.sessions() as session:
            await self._publish(session)
            await self._publish(
                session,
                file_id="NEWFILEID",
                version_name="1.2.0",
                version_code=3,
                file_name="hsk-ai-1.2.0-3-direct-release.apk",
            )
            current = await AndroidReleaseService(session).current()
            self.assertEqual(current.file_id, "NEWFILEID")
            rows = await session.execute(
                select(models.bot_setting.BotSetting).where(
                    models.bot_setting.BotSetting.key == ANDROID_RELEASE_KEY
                )
            )
            self.assertEqual(len(list(rows.scalars())), 1)


class HandingItToALearnerTests(DatabaseBackedTest):
    async def test_the_learner_gets_the_intro_and_the_file(self):
        from app.bot.handlers.android_app import send_android_app

        async with self.sessions() as session:
            await self._add_user(session, language="uz")
            await self._publish(session)
            bot = FakeBot()
            sent = await send_android_app(
                bot, self.CHAT_ID, self.TELEGRAM_ID, session, source="bot_command"
            )

            self.assertTrue(sent)
            self.assertEqual(len(bot.messages), 1)
            self.assertIn("1.1.0 (2)", bot.messages[0][1])
            self.assertIn("3.6 MB", bot.messages[0][1])
            self.assertEqual(len(bot.documents), 1)
            self.assertEqual(bot.documents[0][1], "BQACAgIAAx")
            self.assertIn("O'rnatish", bot.documents[0][2])
            self.assertCountEqual(
                await self._event_names(session),
                ["android_apk_requested", "android_apk_sent"],
            )

    async def test_the_learner_is_answered_in_their_own_language(self):
        from app.bot.handlers.android_app import send_android_app

        for language, marker in (("ru", "Версия"), ("tj", "Версия"), ("uz", "Versiya")):
            with self.subTest(language=language):
                async with self.sessions() as session:
                    await session.execute(User.__table__.delete())
                    await session.execute(CourseMiniAppEvent.__table__.delete())
                    await session.commit()
                    await self._add_user(session, language=language)
                    await self._publish(session)
                    bot = FakeBot()
                    await send_android_app(
                        bot, self.CHAT_ID, self.TELEGRAM_ID, session, source="bot_command"
                    )
                    self.assertIn(marker, bot.messages[0][1])

    async def test_nothing_published_means_no_file_and_an_explanation(self):
        from app.bot.handlers.android_app import send_android_app

        async with self.sessions() as session:
            await self._add_user(session, language="uz")
            bot = FakeBot()
            sent = await send_android_app(
                bot, self.CHAT_ID, self.TELEGRAM_ID, session, source="bot_command"
            )

            self.assertFalse(sent)
            self.assertEqual(bot.documents, [])
            self.assertIn("tayyor emas", bot.messages[0][1])
            # The ask is still worth counting: it is the only measure of how
            # many people want an app that does not exist yet.
            self.assertEqual(await self._event_names(session), ["android_apk_requested"])

    async def test_a_file_id_that_stopped_resolving_is_reported_not_swallowed(self):
        from app.bot.handlers.android_app import send_android_app

        async with self.sessions() as session:
            await self._add_user(session, language="uz")
            await self._publish(session)
            bot = FakeBot(document_fails=True)
            sent = await send_android_app(
                bot, self.CHAT_ID, self.TELEGRAM_ID, session, source="bot_command"
            )

            self.assertFalse(sent)
            self.assertEqual(bot.documents, [])
            self.assertEqual(len(bot.messages), 2)
            self.assertIn("yuborib bo'lmadi", bot.messages[1][1])
            # A failed send is not a delivery.
            self.assertEqual(await self._event_names(session), ["android_apk_requested"])

    async def test_an_unknown_sender_still_gets_the_file(self):
        """Someone who never pressed /start can still install the app."""

        from app.bot.handlers.android_app import send_android_app

        async with self.sessions() as session:
            await self._publish(session)
            bot = FakeBot()
            sent = await send_android_app(
                bot, self.CHAT_ID, self.TELEGRAM_ID, session, source="bot_command"
            )
            self.assertTrue(sent)
            self.assertEqual(len(bot.documents), 1)


class FakeAnswerTarget:
    """Collects whatever a handler writes back into the chat."""

    def __init__(self):
        self.answers: list[str] = []
        self.edits: list[str] = []

    async def answer(self, text=None, **kwargs):
        if text is not None:
            self.answers.append(text)

    async def edit_text(self, text, **kwargs):
        self.edits.append(text)


class FakeMessage(FakeAnswerTarget):
    def __init__(self, *, user_id, document=None, text=None, chat_id=1):
        super().__init__()
        self.from_user = SimpleNamespace(id=user_id)
        self.document = document
        self.text = text
        self.chat = SimpleNamespace(id=chat_id)


class FakeCallback(FakeAnswerTarget):
    def __init__(self, *, user_id, data, bot=None, chat_id=1):
        super().__init__()
        self.from_user = SimpleNamespace(id=user_id)
        self.data = data
        self.message = FakeMessage(user_id=user_id, chat_id=chat_id)
        self.bot = bot


def _document(file_name: str, *, file_size: int = 3_766_687):
    return SimpleNamespace(
        file_name=file_name,
        file_size=file_size,
        file_id="BQACAgIAAx",
        file_unique_id="AgAD1",
    )


class AdminPublishingFlowTests(DatabaseBackedTest):
    """The panel, driven the way an admin drives it."""

    ADMIN_ID = 7965751363

    def _fsm(self):
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.base import StorageKey
        from aiogram.fsm.storage.memory import MemoryStorage

        return FSMContext(
            storage=MemoryStorage(),
            key=StorageKey(bot_id=1, chat_id=1, user_id=self.ADMIN_ID),
        )

    def setUp(self):
        self._admin_patch = unittest.mock.patch(
            "app.bot.handlers.admin_android.settings",
            SimpleNamespace(ADMIN_IDS=str(self.ADMIN_ID)),
        )
        self._admin_patch.start()
        self.addCleanup(self._admin_patch.stop)

    async def test_a_play_build_is_refused_and_nothing_is_published(self):
        from app.bot.handlers.admin_android import receive_apk

        async with self.sessions() as session:
            state = self._fsm()
            message = FakeMessage(
                user_id=self.ADMIN_ID,
                document=_document("hsk-ai-1.1.0-2-play-release.apk"),
            )
            await receive_apk(message, state)

            self.assertIn("tarqatilmaydi", message.answers[0])
            self.assertIn("play", message.answers[0])
            self.assertIsNone(await AndroidReleaseService(session).current())
            self.assertIsNone(await state.get_state())

    async def test_a_debug_build_is_refused_too(self):
        from app.bot.handlers.admin_android import receive_apk

        state = self._fsm()
        message = FakeMessage(
            user_id=self.ADMIN_ID,
            document=_document("hsk-ai-1.1.0-2-direct-debug.apk"),
        )
        await receive_apk(message, state)
        self.assertIn("tarqatilmaydi", message.answers[0])

    async def test_a_file_that_is_not_an_apk_is_refused(self):
        from app.bot.handlers.admin_android import receive_apk

        state = self._fsm()
        message = FakeMessage(user_id=self.ADMIN_ID, document=_document("notes.txt"))
        await receive_apk(message, state)
        self.assertIn("APK emas", message.answers[0])

    async def test_the_release_build_goes_upload_confirm_publish(self):
        from app.bot.handlers.admin_android import publish_apk, receive_apk

        async with self.sessions() as session:
            state = self._fsm()
            message = FakeMessage(user_id=self.ADMIN_ID, document=_document(RELEASE_APK))
            await receive_apk(message, state)

            # The admin is shown exactly what is about to reach every learner.
            self.assertIn("1.1.0 (2)", message.answers[0])
            self.assertIn("3.6 MB", message.answers[0])
            self.assertIsNone(await AndroidReleaseService(session).current())

            callback = FakeCallback(user_id=self.ADMIN_ID, data="adm_android:publish")
            await publish_apk(callback, session, state)

            release = await AndroidReleaseService(session).current()
            self.assertIsNotNone(release)
            self.assertEqual(release.version_name, "1.1.0")
            self.assertEqual(release.version_code, 2)
            self.assertEqual(release.published_by, self.ADMIN_ID)
            self.assertIn("Chiqarildi", callback.message.edits[0])

    async def test_an_unnamed_apk_asks_the_admin_for_the_version(self):
        from app.bot.handlers.admin_android import publish_apk, receive_apk, receive_version

        async with self.sessions() as session:
            from app.bot.fsm.admin_android import AdminAndroidStates

            state = self._fsm()
            upload = FakeMessage(user_id=self.ADMIN_ID, document=_document("app-release.apk"))
            await receive_apk(upload, state)
            self.assertEqual(
                await state.get_state(), AdminAndroidStates.waiting_for_version.state
            )

            typed = FakeMessage(user_id=self.ADMIN_ID, text="1.3.0 (7)")
            await receive_version(typed, state)
            self.assertIn("1.3.0 (7)", typed.answers[0])

            callback = FakeCallback(user_id=self.ADMIN_ID, data="adm_android:publish")
            await publish_apk(callback, session, state)
            release = await AndroidReleaseService(session).current()
            self.assertEqual(release.version_name, "1.3.0")
            self.assertEqual(release.version_code, 7)

    async def test_a_mistyped_version_keeps_the_admin_in_the_same_step(self):
        from app.bot.fsm.admin_android import AdminAndroidStates
        from app.bot.handlers.admin_android import receive_apk, receive_version

        state = self._fsm()
        await receive_apk(
            FakeMessage(user_id=self.ADMIN_ID, document=_document("app-release.apk")), state
        )
        typed = FakeMessage(user_id=self.ADMIN_ID, text="keyinroq")
        await receive_version(typed, state)

        self.assertIn("❌", typed.answers[0])
        self.assertEqual(
            await state.get_state(), AdminAndroidStates.waiting_for_version.state
        )

    async def test_withdrawing_stops_the_handout_immediately(self):
        from app.bot.handlers.admin_android import withdraw_apk

        async with self.sessions() as session:
            await self._publish(session)
            callback = FakeCallback(user_id=self.ADMIN_ID, data="adm_android:withdraw")
            await withdraw_apk(callback, session, self._fsm())

            self.assertIsNone(await AndroidReleaseService(session).current())
            self.assertIn("to'xtatildi", callback.message.edits[0])

    async def test_a_stranger_cannot_publish_anything(self):
        from app.bot.handlers.admin_android import publish_apk, receive_apk

        async with self.sessions() as session:
            state = self._fsm()
            intruder = FakeMessage(user_id=999, document=_document(RELEASE_APK))
            await receive_apk(intruder, state)
            self.assertEqual(intruder.answers, [])

            callback = FakeCallback(user_id=999, data="adm_android:publish")
            await publish_apk(callback, session, state)
            self.assertIsNone(await AndroidReleaseService(session).current())


class WiringTests(unittest.TestCase):
    def test_the_funnel_events_are_registered(self):
        self.assertIn("android_apk_requested", COURSE_MINIAPP_EVENT_NAMES)
        self.assertIn("android_apk_sent", COURSE_MINIAPP_EVENT_NAMES)

    def test_every_learner_facing_string_exists_in_all_three_languages(self):
        keys = (
            "android_app_button",
            "android_app_intro",
            "android_app_caption",
            "android_app_unavailable",
            "android_app_failed",
        )
        for language in ("uz", "ru", "tj"):
            for key in keys:
                with self.subTest(language=language, key=key):
                    self.assertIn(key, TEXTS[language])
                    self.assertTrue(TEXTS[language][key].strip())

    def test_the_profile_keyboard_offers_the_app_in_every_language(self):
        from app.bot.handlers.android_app import ANDROID_APP_CALLBACK
        from app.bot.handlers.commands import profile_menu_keyboard

        for language in ("uz", "ru", "tj"):
            with self.subTest(language=language):
                keyboard = profile_menu_keyboard(language)
                buttons = [
                    button
                    for row in keyboard.inline_keyboard
                    for button in row
                    if button.callback_data == ANDROID_APP_CALLBACK
                ]
                self.assertEqual(len(buttons), 1)
                self.assertEqual(buttons[0].text, TEXTS[language]["android_app_button"])

    def test_the_admin_panel_button_reaches_a_real_handler(self):
        from app.bot.handlers.admin import admin_menu_keyboard
        from app.bot.handlers.admin_android import PANEL_CALLBACK, router

        panel_buttons = [
            button
            for row in admin_menu_keyboard().inline_keyboard
            for button in row
            if button.callback_data == PANEL_CALLBACK
        ]
        self.assertEqual(len(panel_buttons), 1)

        # Resolve a stand-in callback query against the registered filters
        # rather than reading their source: a button whose data no longer
        # matches any filter is exactly the dead control this guards against.
        pressed = SimpleNamespace(data=PANEL_CALLBACK)
        matched = [
            handler.callback.__name__
            for handler in router.observers["callback_query"].handlers
            if all(f.callback(pressed) for f in (handler.filters or ()))
        ]
        self.assertTrue(matched, "the admin panel button has no handler behind it")

    def test_no_earlier_router_swallows_the_android_command(self):
        """Walk the real dispatcher in real order and see who claims /android.

        Router order is the one thing a unit test of the handler cannot check:
        every handler here passes its own tests while an earlier router quietly
        answers first and the command appears to do nothing.

        It runs in a subprocess because building a Dispatcher attaches every
        module-level router to it permanently — doing that in this process
        would make the next `create_bot()` anywhere in the suite raise
        "Router is already attached".
        """

        import subprocess
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        probe = """
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from aiogram.types import Chat, Message
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
sessions = async_sessionmaker(engine, expire_on_commit=False)
with patch("app.bot.create_bot.async_session_maker", sessions):
    from app.bot.create_bot import create_bot
    bot, dispatcher = create_bot(
        type("S", (), {"BOT_TOKEN": "123456:AAHtest-token-value-here"})
    )

message = Message(
    message_id=1,
    date=datetime.now(timezone.utc),
    chat=Chat(id=5150, type="private"),
    from_user=TelegramUser(id=5150, is_bot=False, first_name="T"),
    text="/android",
)


async def claims(handler):
    for handler_filter in handler.filters or ():
        try:
            result = handler_filter.callback(message)
            if asyncio.iscoroutine(result):
                result = await result
        except TypeError:
            try:
                result = await handler_filter.callback(message, bot=bot)
            except Exception:
                return False
        except Exception:
            return False
        if not result:
            return False
    return True


async def main():
    routers = []

    def walk(router):
        routers.append(router)
        for sub in router.sub_routers:
            walk(sub)

    walk(dispatcher)
    for router in routers:
        for handler in router.observers["message"].handlers:
            if await claims(handler):
                print(handler.callback.__name__)
                return
    print("NOBODY")


asyncio.run(main())
"""
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertEqual(result.stdout.strip().splitlines()[-1], "android_command")

    def test_both_routers_are_wired_into_the_bot(self):
        from app.bot import create_bot as module

        source = __import__("pathlib").Path(module.__file__).read_text(encoding="utf-8")
        self.assertIn("dp.include_router(android_app_router)", source)
        self.assertIn("dp.include_router(admin_android_router)", source)


class AdminGuardTests(unittest.TestCase):
    def test_a_non_admin_cannot_reach_the_panel(self):
        from app.bot.handlers.admin_android import _is_admin

        with unittest.mock.patch(
            "app.bot.handlers.admin_android.settings",
            SimpleNamespace(ADMIN_IDS="7965751363"),
        ):
            self.assertTrue(_is_admin(7965751363))
            self.assertFalse(_is_admin(1))


if __name__ == "__main__":
    unittest.main()
