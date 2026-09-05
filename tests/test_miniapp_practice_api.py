"""Mini App mashq adapteri.

Adapterda biznes mantiq yo'q — u Telegram initData'ni tekshiradi va
`CourseMiniAppPracticeService` ga uzatadi. Shuning uchun testlar aynan
adapterning mas'uliyatini qoplaydi:

1. Imzosiz/soxta initData bilan hech narsa ochilmaydi.
2. Ruxsat SERVIS ichida QAYTA tekshirilmaydi (`gate_checked=True`) — Mini App
   o'zining daily-gate/ad-gate yo'lidan yuradi va uning limiti boshqa
   (umrbod, boshqa feature kaliti). Qarang ARCHITECTURE_DECISION.md, Qaror A.
3. Noto'g'ri so'rov 500 emas, tushunarli xato bo'lib qaytadi.
"""

import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.miniapp_practice import create_miniapp_practice_router


VALID_INIT_DATA = "query_id=AAA&user=%7B%22id%22%3A123%7D&hash=deadbeef"


@asynccontextmanager
async def _session():
    yield SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())


def _session_factory():
    return _session()


def build_client(service, *, telegram_id=123, drill_service=None, mastery_service=None):
    app = FastAPI()
    app.include_router(
        create_miniapp_practice_router(
            session_factory=_session_factory,
            settings_obj=SimpleNamespace(BOT_TOKEN="123:test"),
            service_factory=lambda session, bot=None: service,
            drill_service_factory=lambda session: drill_service
            or SimpleNamespace(record=AsyncMock(return_value=0)),
            mastery_service_factory=lambda session: mastery_service
            or SimpleNamespace(
                record_drill=AsyncMock(return_value=0),
                drill_words=AsyncMock(
                    return_value={"skill": "recognition", "day": "2026-09-05", "words": []}
                ),
            ),
        )
    )
    transport = ASGITransport(app=app)
    verifier = patch(
        "app.api.miniapp_practice.extract_verified_webapp_user_id",
        return_value=telegram_id,
    )
    return AsyncClient(transport=transport, base_url="http://test"), verifier


def practice_service(start_result=None, complete_result=None):
    return SimpleNamespace(
        start=AsyncMock(return_value=start_result or {"ok": True, "session": {"id": "s", "questions": []}}),
        complete=AsyncMock(return_value=complete_result or {"ok": True, "score": 1, "total": 1}),
    )


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_without_init_data_is_rejected(self):
        service = practice_service()
        client, verifier = build_client(service, telegram_id=None)
        async with client:
            with verifier:
                response = await client.post(
                    "/api/v3/practice/start",
                    json={"mode": "mock", "level": "hsk1", "language": "uz"},
                )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "invalid_telegram_init_data")
        service.start.assert_not_awaited()

    async def test_header_init_data_is_accepted(self):
        service = practice_service()
        client, verifier = build_client(service)
        async with client:
            with verifier:
                response = await client.post(
                    "/api/v3/practice/start",
                    json={"mode": "mock", "level": "hsk1", "language": "uz"},
                    headers={"X-Telegram-Init-Data": VALID_INIT_DATA},
                )

        self.assertEqual(response.status_code, 200)
        service.start.assert_awaited_once()


class GateOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_does_not_re_check_the_gate(self):
        # Servisning o'z gate'i `training_test` slotini sarflaydi, uni Xatolar
        # bo'limi va Test markazi ham bo'lishadi. Mini App bu yo'ldan yursa,
        # bitta ieroglif mashqi o'quvchining Xatolar bo'limini yopib qo'yardi.
        service = practice_service()
        client, verifier = build_client(service)
        async with client:
            with verifier:
                await client.post(
                    "/api/v3/practice/start",
                    json={
                        "mode": "training",
                        "level": "hsk1",
                        "language": "uz",
                        "skill": "listening",
                        "initData": VALID_INIT_DATA,
                    },
                )

        self.assertTrue(service.start.await_args.kwargs["gate_checked"])

    async def test_complete_does_not_re_check_the_gate(self):
        service = practice_service()
        client, verifier = build_client(service)
        async with client:
            with verifier:
                await client.post(
                    "/api/v3/practice/complete",
                    json={
                        "mode": "mock",
                        "level": "hsk1",
                        "language": "uz",
                        "session_id": "practice:1:x",
                        "answers": [{"question_id": "q1", "selected": 2}],
                        "initData": VALID_INIT_DATA,
                    },
                )

        self.assertTrue(service.complete.await_args.kwargs["gate_checked"])

    async def test_client_cannot_pass_an_ad_flag_or_access_ref(self):
        # Reklama yo'li Mini App tomonda hal qilinadi; adapter uni qabul
        # qilmaydi, shuning uchun mijoz servis gate'ini aylanib o'tolmaydi.
        service = practice_service()
        client, verifier = build_client(service)
        async with client:
            with verifier:
                response = await client.post(
                    "/api/v3/practice/start",
                    json={
                        "mode": "mock",
                        "level": "hsk1",
                        "language": "uz",
                        "ad_supported": True,
                        "initData": VALID_INIT_DATA,
                    },
                )

        self.assertEqual(response.status_code, 422)
        service.start.assert_not_awaited()


class AnswerForwardingTests(unittest.IsolatedAsyncioTestCase):
    async def test_answers_reach_the_service_in_the_expected_shape(self):
        service = practice_service()
        client, verifier = build_client(service)
        async with client:
            with verifier:
                await client.post(
                    "/api/v3/practice/complete",
                    json={
                        "mode": "training",
                        "level": "hsk1",
                        "language": "ru",
                        "skill": "characters",
                        "session_id": "practice:1:x",
                        "answers": [
                            {"question_id": "q1", "selected": 0},
                            {"question_id": "q2", "selected": 3},
                        ],
                        "initData": VALID_INIT_DATA,
                    },
                )

        self.assertEqual(
            service.complete.await_args.kwargs["answers"],
            [
                {"question_id": "q1", "selected_index": 0},
                {"question_id": "q2", "selected_index": 3},
            ],
        )


class ValidationTests(unittest.IsolatedAsyncioTestCase):
    async def _post(self, service, path, payload, **kwargs):
        client, verifier = build_client(service)
        async with client:
            with verifier:
                return await client.post(path, json=payload, **kwargs)

    async def test_training_needs_a_known_skill(self):
        service = practice_service()
        response = await self._post(
            service,
            "/api/v3/practice/start",
            {
                "mode": "training",
                "level": "hsk1",
                "language": "uz",
                "skill": "dancing",
                "initData": VALID_INIT_DATA,
            },
        )

        self.assertEqual(response.status_code, 422)
        service.start.assert_not_awaited()

    async def test_non_training_mode_must_not_carry_a_skill(self):
        service = practice_service()
        response = await self._post(
            service,
            "/api/v3/practice/start",
            {
                "mode": "mock",
                "level": "hsk1",
                "language": "uz",
                "skill": "listening",
                "initData": VALID_INIT_DATA,
            },
        )

        self.assertEqual(response.status_code, 422)

    async def test_unknown_language_is_rejected(self):
        service = practice_service()
        response = await self._post(
            service,
            "/api/v3/practice/start",
            {"mode": "mock", "level": "hsk1", "language": "en", "initData": VALID_INIT_DATA},
        )

        self.assertEqual(response.status_code, 422)

    async def test_too_many_answers_are_rejected(self):
        service = practice_service()
        response = await self._post(
            service,
            "/api/v3/practice/complete",
            {
                "mode": "mock",
                "level": "hsk1",
                "language": "uz",
                "session_id": "practice:1:x",
                "answers": [{"question_id": f"q{n}", "selected": 0} for n in range(101)],
                "initData": VALID_INIT_DATA,
            },
        )

        self.assertEqual(response.status_code, 413)
        service.complete.assert_not_awaited()

    async def test_non_json_body_is_rejected(self):
        service = practice_service()
        client, verifier = build_client(service)
        async with client:
            with verifier:
                response = await client.post(
                    "/api/v3/practice/start",
                    content=b"mode=mock",
                    headers={"Content-Type": "text/plain"},
                )

        self.assertEqual(response.status_code, 415)


class ServiceRefusalTests(unittest.IsolatedAsyncioTestCase):
    async def test_access_refusal_is_a_403_not_a_500(self):
        service = practice_service(
            start_result={"ok": False, "error": "free_feature_limit_reached"}
        )
        client, verifier = build_client(service)
        async with client:
            with verifier:
                response = await client.post(
                    "/api/v3/practice/start",
                    json={"mode": "mock", "level": "hsk1", "language": "uz", "initData": VALID_INIT_DATA},
                )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "free_feature_limit_reached")

    async def test_missing_questions_is_a_409(self):
        service = practice_service(
            start_result={"ok": False, "error": "practice_questions_not_found"}
        )
        client, verifier = build_client(service)
        async with client:
            with verifier:
                response = await client.post(
                    "/api/v3/practice/start",
                    json={"mode": "mock", "level": "hsk1", "language": "uz", "initData": VALID_INIT_DATA},
                )

        self.assertEqual(response.status_code, 409)

    async def test_unexpected_service_failure_is_reported_as_unavailable(self):
        service = practice_service()
        service.start = AsyncMock(side_effect=RuntimeError("boom"))
        client, verifier = build_client(service)
        async with client:
            with verifier:
                response = await client.post(
                    "/api/v3/practice/start",
                    json={"mode": "mock", "level": "hsk1", "language": "uz", "initData": VALID_INIT_DATA},
                )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "practice_unavailable")


class DrillReportTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _user_repo(user=SimpleNamespace(id=3, telegram_id=123)):
        return patch(
            "app.api.miniapp_practice.UserRepository",
            return_value=SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user)),
        )

    async def _report(self, drill, payload, *, user=SimpleNamespace(id=3, telegram_id=123)):
        client, verifier = build_client(practice_service(), drill_service=drill)
        async with client:
            with verifier, self._user_repo(user):
                return await client.post("/api/v3/practice/report", json=payload)

    async def test_wrong_characters_reach_the_drill_signal_service(self):
        drill = SimpleNamespace(record=AsyncMock(return_value=2))
        response = await self._report(
            drill,
            {
                "feature": "recognition",
                "level": "hsk1",
                "language": "uz",
                "mistakes": [{"hanzi": "你", "selected": "好"}, {"hanzi": "好"}],
                "initData": VALID_INIT_DATA,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recorded"], 2)
        self.assertEqual(
            drill.record.await_args.kwargs["entries"],
            [{"hanzi": "你", "selected": "好"}, {"hanzi": "好", "selected": ""}],
        )

    async def test_client_cannot_send_a_prompt_or_a_correct_answer(self):
        # Savol va to'g'ri javob faqat server lug'atidan quriladi, shuning
        # uchun adapter qo'shimcha maydonlarni umuman qabul qilmaydi.
        drill = SimpleNamespace(record=AsyncMock(return_value=0))
        response = await self._report(
            drill,
            {
                "feature": "recognition",
                "level": "hsk1",
                "language": "uz",
                "mistakes": [{"hanzi": "你", "correct_answer": "好", "question": "soxta"}],
                "initData": VALID_INIT_DATA,
            },
        )

        self.assertEqual(response.status_code, 422)
        drill.record.assert_not_awaited()

    async def test_unknown_feature_is_rejected(self):
        drill = SimpleNamespace(record=AsyncMock())
        response = await self._report(
            drill,
            {
                "feature": "voice",
                "level": "hsk1",
                "language": "uz",
                "mistakes": [{"hanzi": "你"}],
                "initData": VALID_INIT_DATA,
            },
        )

        self.assertEqual(response.status_code, 422)
        drill.record.assert_not_awaited()

    async def test_unknown_user_is_refused_without_touching_the_service(self):
        drill = SimpleNamespace(record=AsyncMock())
        response = await self._report(
            drill,
            {
                "feature": "recognition",
                "level": "hsk1",
                "language": "uz",
                "mistakes": [{"hanzi": "你"}],
                "initData": VALID_INIT_DATA,
            },
            user=None,
        )

        self.assertEqual(response.status_code, 403)
        drill.record.assert_not_awaited()

    async def test_report_without_init_data_is_rejected(self):
        drill = SimpleNamespace(record=AsyncMock())
        client, verifier = build_client(
            practice_service(), telegram_id=None, drill_service=drill
        )
        async with client:
            with verifier, self._user_repo():
                response = await client.post(
                    "/api/v3/practice/report",
                    json={
                        "feature": "recognition",
                        "level": "hsk1",
                        "language": "uz",
                        "mistakes": [{"hanzi": "你"}],
                    },
                )

        self.assertEqual(response.status_code, 401)
        drill.record.assert_not_awaited()


class DrillWordsTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _user_repo(user=SimpleNamespace(id=3, telegram_id=123)):
        return patch(
            "app.api.miniapp_practice.UserRepository",
            return_value=SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user)),
        )

    async def _words(self, mastery, payload, *, user=SimpleNamespace(id=3, telegram_id=123)):
        client, verifier = build_client(practice_service(), mastery_service=mastery)
        async with client:
            with verifier, self._user_repo(user):
                return await client.post("/api/v3/practice/words", json=payload)

    async def test_the_selected_words_reach_the_client(self):
        mastery = SimpleNamespace(
            drill_words=AsyncMock(
                return_value={
                    "skill": "recognition",
                    "day": "2026-09-05",
                    "words": [
                        {"zh": "你", "kind": "review", "box": 1},
                        {"zh": "好", "kind": "new", "box": 0},
                    ],
                }
            )
        )
        response = await self._words(
            mastery,
            {"feature": "recognition", "limit": 10, "initData": VALID_INIT_DATA},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([item["zh"] for item in body["words"]], ["你", "好"])
        self.assertEqual(mastery.drill_words.await_args.kwargs["skill"], "recognition")
        self.assertEqual(mastery.drill_words.await_args.kwargs["limit"], 10)

    async def test_the_response_carries_no_user_facing_text(self):
        # Ko'rinadigan matn klientda qoladi, shuning uchun til almashganda
        # server javobi o'zgarmaydi.
        mastery = SimpleNamespace(
            drill_words=AsyncMock(
                return_value={
                    "skill": "recognition",
                    "day": "2026-09-05",
                    "words": [{"zh": "你", "kind": "review", "box": 1}],
                }
            )
        )
        response = await self._words(
            mastery, {"feature": "recognition", "initData": VALID_INIT_DATA}
        )

        self.assertEqual(set(response.json()["words"][0]), {"zh", "kind", "box"})

    async def test_an_empty_selection_is_not_an_error(self):
        # Bo'sh ro'yxat nosozlik emas — klient o'z pooliga qaytadi.
        mastery = SimpleNamespace(
            drill_words=AsyncMock(
                return_value={"skill": "recognition", "day": "2026-09-05", "words": []}
            )
        )
        response = await self._words(
            mastery, {"feature": "recognition", "initData": VALID_INIT_DATA}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["words"], [])

    async def test_only_the_two_wired_drills_are_accepted(self):
        mastery = SimpleNamespace(drill_words=AsyncMock())
        response = await self._words(
            mastery, {"feature": "memorize", "initData": VALID_INIT_DATA}
        )

        self.assertEqual(response.status_code, 422)
        mastery.drill_words.assert_not_awaited()

    async def test_an_unsigned_request_selects_nothing(self):
        mastery = SimpleNamespace(drill_words=AsyncMock())
        client, verifier = build_client(
            practice_service(), telegram_id=None, mastery_service=mastery
        )
        async with client:
            with verifier, self._user_repo():
                response = await client.post(
                    "/api/v3/practice/words", json={"feature": "recognition"}
                )

        self.assertEqual(response.status_code, 401)
        mastery.drill_words.assert_not_awaited()

    async def test_an_unknown_user_is_refused(self):
        mastery = SimpleNamespace(drill_words=AsyncMock())
        response = await self._words(
            mastery, {"feature": "recognition", "initData": VALID_INIT_DATA}, user=None
        )

        self.assertEqual(response.status_code, 403)
        mastery.drill_words.assert_not_awaited()

    async def test_an_absurd_limit_is_rejected(self):
        mastery = SimpleNamespace(drill_words=AsyncMock())
        response = await self._words(
            mastery,
            {"feature": "recognition", "limit": 500, "initData": VALID_INIT_DATA},
        )

        self.assertEqual(response.status_code, 422)


class DrillResultsTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _user_repo(user=SimpleNamespace(id=3, telegram_id=123)):
        return patch(
            "app.api.miniapp_practice.UserRepository",
            return_value=SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user)),
        )

    async def _report(self, payload, *, drill=None, mastery=None):
        drill = drill or SimpleNamespace(record=AsyncMock(return_value=0))
        mastery = mastery or SimpleNamespace(record_drill=AsyncMock(return_value=0))
        client, verifier = build_client(
            practice_service(), drill_service=drill, mastery_service=mastery
        )
        async with client:
            with verifier, self._user_repo():
                response = await client.post("/api/v3/practice/report", json=payload)
        return response, drill, mastery

    async def test_results_are_scheduled_for_interval_review(self):
        response, _, mastery = await self._report(
            {
                "feature": "recognition",
                "level": "hsk1",
                "language": "uz",
                "results": [{"hanzi": "你", "correct": True}, {"hanzi": "好", "correct": False}],
                "initData": VALID_INIT_DATA,
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mastery.record_drill.await_args.kwargs["results"],
            [{"hanzi": "你", "correct": True}, {"hanzi": "好", "correct": False}],
        )

    async def test_a_legacy_mistakes_only_body_still_works(self):
        # Yodlash bo'limi hali shu yo'ldan yuradi.
        response, drill, mastery = await self._report(
            {
                "feature": "memorize",
                "level": "hsk1",
                "language": "uz",
                "mistakes": [{"hanzi": "你"}],
                "initData": VALID_INIT_DATA,
            }
        )

        self.assertEqual(response.status_code, 200)
        drill.record.assert_awaited_once()
        mastery.record_drill.assert_not_awaited()

    async def test_pronunciation_may_not_write_mistakes(self):
        # Uning xatosini server `score_pronunciation` ichida yozadi —
        # bu yerda qabul qilinsa dublikat qator paydo bo'lardi.
        response, drill, _ = await self._report(
            {
                "feature": "pronunciation",
                "level": "hsk1",
                "language": "uz",
                "mistakes": [{"hanzi": "你"}],
                "initData": VALID_INIT_DATA,
            }
        )

        self.assertEqual(response.status_code, 422)
        drill.record.assert_not_awaited()

    async def test_pronunciation_may_not_claim_a_success(self):
        # To'g'ri talaffuzni faqat server baholay oladi.
        response, _, mastery = await self._report(
            {
                "feature": "pronunciation",
                "level": "hsk1",
                "language": "uz",
                "results": [{"hanzi": "你", "correct": True}],
                "initData": VALID_INIT_DATA,
            }
        )

        self.assertEqual(response.status_code, 422)
        mastery.record_drill.assert_not_awaited()

    async def test_pronunciation_may_report_a_skip_or_a_third_failure(self):
        response, _, mastery = await self._report(
            {
                "feature": "pronunciation",
                "level": "hsk1",
                "language": "uz",
                "results": [{"hanzi": "你", "correct": False}],
                "initData": VALID_INIT_DATA,
            }
        )

        self.assertEqual(response.status_code, 200)
        mastery.record_drill.assert_awaited_once()

    async def test_an_empty_report_is_rejected(self):
        response, drill, mastery = await self._report(
            {
                "feature": "recognition",
                "level": "hsk1",
                "language": "uz",
                "initData": VALID_INIT_DATA,
            }
        )

        self.assertEqual(response.status_code, 422)
        drill.record.assert_not_awaited()
        mastery.record_drill.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
