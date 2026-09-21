import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.ios_practice import create_ios_practice_router


class IOSPracticeTransportTests(unittest.IsolatedAsyncioTestCase):
    async def _client(
        self, service, mistake_service=None, exam_service=None,
        mastery_service=None, drill_service=None, voice_service=None,
    ):
        @asynccontextmanager
        async def session_factory():
            yield object()

        app = FastAPI()
        app.include_router(
            create_ios_practice_router(
                session_factory=session_factory,
                settings_obj=SimpleNamespace(),
                service_factory=lambda *_args, **_kwargs: service,
                mistake_service_factory=lambda *_args, **_kwargs: (
                    mistake_service if mistake_service is not None else SimpleNamespace()
                ),
                exam_service_factory=lambda *_args, **_kwargs: (
                    exam_service if exam_service is not None else SimpleNamespace()
                ),
                mastery_service_factory=lambda *_args, **_kwargs: (
                    mastery_service if mastery_service is not None else SimpleNamespace()
                ),
                drill_service_factory=lambda *_args, **_kwargs: (
                    drill_service if drill_service is not None else SimpleNamespace()
                ),
                voice_service_factory=lambda *_args, **_kwargs: (
                    voice_service if voice_service is not None else SimpleNamespace()
                ),
            )
        )
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://testserver",
        )

    async def test_start_delegates_to_shared_practice_service(self):
        service = SimpleNamespace(
            start=AsyncMock(
                return_value={
                    "ok": True,
                    "session": {
                        "id": "session-123",
                        "mode": "placement",
                        "skill": "",
                        "level": "hsk3",
                        "questions": [],
                    },
                }
            )
        )
        fake_context = SimpleNamespace(
            user=SimpleNamespace(telegram_id=123456)
        )

        with patch(
            "app.api.ios_practice.DesktopAuthService.authenticate",
            new=AsyncMock(return_value=fake_context),
        ):
            async with await self._client(service) as client:
                response = await client.post(
                    "/api/v3/ios/practice/start",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "mode": "placement",
                        "level": "hsk3",
                        "language": "uz",
                        "skill": "",
                        "access_ref": "",
                        "ad_supported": False,
                    },
                )

        self.assertEqual(200, response.status_code)
        service.start.assert_awaited_once_with(
            123456,
            mode="placement",
            level="hsk3",
            lang="uz",
            skill="",
            access_ref="",
            ad_supported=False,
        )

    async def test_complete_maps_selected_answers_to_server_shape(self):
        service = SimpleNamespace(
            complete=AsyncMock(
                return_value={
                    "ok": True,
                    "score": 1,
                    "total": 1,
                    "percent": 100,
                    "recommendation": "",
                    "wrong_items": [],
                }
            )
        )
        fake_context = SimpleNamespace(
            user=SimpleNamespace(telegram_id=123456)
        )

        with patch(
            "app.api.ios_practice.DesktopAuthService.authenticate",
            new=AsyncMock(return_value=fake_context),
        ):
            async with await self._client(service) as client:
                response = await client.post(
                    "/api/v3/ios/practice/complete",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "mode": "training",
                        "level": "hsk2",
                        "language": "ru",
                        "skill": "listening",
                        "session_id": "session-123",
                        "answers": [
                            {"question_id": "q1", "selected": 2}
                        ],
                        "access_ref": "",
                        "ad_supported": False,
                    },
                )

        self.assertEqual(200, response.status_code)
        service.complete.assert_awaited_once_with(
            123456,
            session_id="session-123",
            mode="training",
            level="hsk2",
            lang="ru",
            skill="listening",
            answers=[
                {"question_id": "q1", "selected_index": 2}
            ],
            access_ref="",
            ad_supported=False,
        )




    async def test_drill_words_use_server_mastery_plan(self):
        service = SimpleNamespace()
        mastery_service = SimpleNamespace(drill_words=AsyncMock(return_value={
            "skill": "recognition", "day": "2026-09-21",
            "words": [{"zh": "你", "kind": "new", "box": 0}],
        }))
        fake_context = SimpleNamespace(user=SimpleNamespace(telegram_id=123456))
        user = SimpleNamespace(id=77, telegram_id=123456, level="hsk3", language="uz")
        fake_session = unittest.mock.MagicMock()
        fake_session.commit = AsyncMock()

        @asynccontextmanager
        async def session_factory():
            yield fake_session

        app = FastAPI()
        app.include_router(create_ios_practice_router(
            session_factory=session_factory,
            settings_obj=SimpleNamespace(),
            service_factory=lambda *_args, **_kwargs: service,
            mastery_service_factory=lambda *_args, **_kwargs: mastery_service,
        ))
        with (
            patch("app.api.ios_practice.DesktopAuthService.authenticate",
                  new=AsyncMock(return_value=fake_context)),
            patch("app.api.ios_practice.UserRepository.get_by_telegram_id",
                  new=AsyncMock(return_value=user)),
        ):
            async with AsyncClient(transport=ASGITransport(app=app),
                                   base_url="https://testserver") as client:
                response = await client.post(
                    "/api/v3/ios/practice/words",
                    headers={"Authorization": "Bearer access-token"},
                    json={"feature": "recognition", "limit": 10},
                )

        self.assertEqual(200, response.status_code)
        self.assertEqual("你", response.json()["words"][0]["zh"])
        mastery_service.drill_words.assert_awaited_once_with(
            user, skill="recognition", limit=10
        )

    async def test_drill_report_keeps_server_side_mistake_rebuild(self):
        service = SimpleNamespace()
        mastery_service = SimpleNamespace(record_drill=AsyncMock(return_value=1))
        drill_service = SimpleNamespace(record=AsyncMock(return_value=1))
        fake_context = SimpleNamespace(user=SimpleNamespace(telegram_id=123456))
        user = SimpleNamespace(id=77, telegram_id=123456, level="hsk3", language="uz")
        fake_session = unittest.mock.MagicMock()
        fake_session.commit = AsyncMock()

        @asynccontextmanager
        async def session_factory():
            yield fake_session

        app = FastAPI()
        app.include_router(create_ios_practice_router(
            session_factory=session_factory,
            settings_obj=SimpleNamespace(),
            service_factory=lambda *_args, **_kwargs: service,
            mastery_service_factory=lambda *_args, **_kwargs: mastery_service,
            drill_service_factory=lambda *_args, **_kwargs: drill_service,
        ))
        with (
            patch("app.api.ios_practice.DesktopAuthService.authenticate",
                  new=AsyncMock(return_value=fake_context)),
            patch("app.api.ios_practice.UserRepository.get_by_telegram_id",
                  new=AsyncMock(return_value=user)),
        ):
            async with AsyncClient(transport=ASGITransport(app=app),
                                   base_url="https://testserver") as client:
                response = await client.post(
                    "/api/v3/ios/practice/report",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "feature": "recognition", "level": "hsk3", "language": "uz",
                        "mistakes": [{"hanzi": "你", "selected": "好"}],
                        "results": [{"hanzi": "你", "correct": False}],
                    },
                )

        self.assertEqual(200, response.status_code)
        drill_service.record.assert_awaited_once_with(
            user, feature="recognition", level="hsk3", language="uz",
            entries=[{"hanzi": "你", "selected": "好"}],
        )
        mastery_service.record_drill.assert_awaited_once_with(
            user, skill="recognition", results=[{"hanzi": "你", "correct": False}]
        )


    async def test_pronunciation_delegates_audio_to_shared_voice_service(self):
        service = SimpleNamespace()
        voice_service = SimpleNamespace(
            score_pronunciation=AsyncMock(return_value={
                "ok": True, "score": 86, "passed": True,
                "heard": "你", "message": "",
            })
        )
        fake_context = SimpleNamespace(user=SimpleNamespace(telegram_id=123456))
        audio = "data:audio/mp4;base64,QUJDRA=="

        with patch(
            "app.api.ios_practice.DesktopAuthService.authenticate",
            new=AsyncMock(return_value=fake_context),
        ):
            async with await self._client(service, voice_service=voice_service) as client:
                response = await client.post(
                    "/api/v3/ios/voice/pronounce",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "target": "你",
                        "target_pinyin": "nǐ",
                        "language": "uz",
                        "level": "hsk1",
                        "audio_data_url": audio,
                    },
                )

        self.assertEqual(200, response.status_code)
        voice_service.score_pronunciation.assert_awaited_once()
        call = voice_service.score_pronunciation.await_args
        self.assertEqual(123456, call.args[0])
        self.assertEqual("你", call.kwargs["target"])
        self.assertEqual("nǐ", call.kwargs["target_pinyin"])
        self.assertEqual(b"ABCD", call.kwargs["audio_bytes"])
        self.assertEqual("uz", call.kwargs["language"])
        self.assertEqual("hsk1", call.kwargs["level"])

    async def test_exam_start_preserves_assessment_lifecycle(self):
        service = SimpleNamespace()
        exam_service = SimpleNamespace(
            start=AsyncMock(return_value={
                "ok": True,
                "session": {
                    "id": "exam-session-123",
                    "level": "hsk3",
                    "duration_min": 35,
                    "pass_score": 60,
                    "questions": [],
                },
            })
        )
        fake_context = SimpleNamespace(
            user=SimpleNamespace(id=77, telegram_id=123456)
        )

        with (
            patch(
                "app.api.ios_practice.DesktopAuthService.authenticate",
                new=AsyncMock(return_value=fake_context),
            ),
            patch(
                "app.api.ios_practice.assessment_abandoned",
                new=AsyncMock(return_value=False),
            ) as abandoned,
            patch(
                "app.api.ios_practice.assessment_started",
                new=AsyncMock(),
            ) as started,
        ):
            async with await self._client(service, exam_service=exam_service) as client:
                response = await client.post(
                    "/api/v3/ios/exams/start",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "level": "hsk3",
                        "language": "uz",
                        "access_ref": "",
                        "ad_supported": False,
                    },
                )

        self.assertEqual(200, response.status_code)
        exam_service.start.assert_awaited_once_with(
            123456,
            level="hsk3",
            lang="uz",
            access_ref="",
            ad_supported=False,
        )
        abandoned.assert_awaited_once_with(
            unittest.mock.ANY,
            77,
            "exam-session-123",
        )
        started.assert_awaited_once_with(
            unittest.mock.ANY,
            77,
            "exam",
            unittest.mock.ANY,
        )

    async def test_exam_complete_finishes_assessment(self):
        service = SimpleNamespace()
        exam_service = SimpleNamespace(
            complete=AsyncMock(return_value={
                "ok": True,
                "score": 10,
                "total": 12,
                "percent": 83,
                "pass_score": 60,
                "passed": True,
                "section_scores": {},
                "wrong_items": [],
            })
        )
        fake_context = SimpleNamespace(
            user=SimpleNamespace(id=77, telegram_id=123456)
        )

        with (
            patch(
                "app.api.ios_practice.DesktopAuthService.authenticate",
                new=AsyncMock(return_value=fake_context),
            ),
            patch(
                "app.api.ios_practice.assessment_abandoned",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "app.api.ios_practice.assessment_finished",
                new=AsyncMock(),
            ) as finished,
        ):
            async with await self._client(service, exam_service=exam_service) as client:
                response = await client.post(
                    "/api/v3/ios/exams/complete",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "session_id": "exam-session-123",
                        "level": "hsk3",
                        "language": "ru",
                        "answers": [
                            {"question_id": "q1", "selected_index": 1}
                        ],
                    },
                )

        self.assertEqual(200, response.status_code)
        exam_service.complete.assert_awaited_once_with(
            123456,
            session_id="exam-session-123",
            answers=[{"question_id": "q1", "selected_index": 1}],
            level="hsk3",
            lang="ru",
        )
        finished.assert_awaited_once_with(
            unittest.mock.ANY,
            77,
            "exam-session-123",
        )

    async def test_mistakes_overview_delegates_pagination(self):
        service = SimpleNamespace()
        mistake_service = SimpleNamespace(
            overview=AsyncMock(return_value={
                "ok": True,
                "summary": {"total": 1, "categories": {"grammar": 1}},
                "items": [],
            })
        )
        fake_context = SimpleNamespace(user=SimpleNamespace(telegram_id=123456))

        with patch(
            "app.api.ios_practice.DesktopAuthService.authenticate",
            new=AsyncMock(return_value=fake_context),
        ):
            async with await self._client(service, mistake_service) as client:
                response = await client.get(
                    "/api/v3/ios/mistakes?category=grammar&limit=30&offset=0",
                    headers={"Authorization": "Bearer access-token"},
                )

        self.assertEqual(200, response.status_code)
        mistake_service.overview.assert_awaited_once_with(
            123456,
            category="grammar",
            limit="30",
            offset="0",
        )

    async def test_mistake_review_answer_uses_server_grading(self):
        service = SimpleNamespace()
        mistake_service = SimpleNamespace(
            answer_review_question=AsyncMock(return_value={
                "ok": True,
                "question_id": "mistake-q1",
                "selected_index": 1,
                "correct": False,
                "correct_index": 0,
                "correct_answer": "你好",
                "explanation": "你好 = Salom",
            })
        )
        fake_context = SimpleNamespace(user=SimpleNamespace(telegram_id=123456))

        with patch(
            "app.api.ios_practice.DesktopAuthService.authenticate",
            new=AsyncMock(return_value=fake_context),
        ):
            async with await self._client(service, mistake_service) as client:
                response = await client.post(
                    "/api/v3/ios/mistakes/review/answer",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "session_id": "session-123",
                        "question_id": "mistake-q1",
                        "selected_index": 1,
                    },
                )

        self.assertEqual(200, response.status_code)
        self.assertFalse(response.json()["correct"])
        mistake_service.answer_review_question.assert_awaited_once_with(
            123456,
            session_id="session-123",
            question_id="mistake-q1",
            selected_index=1,
        )

    async def test_training_rejects_unknown_skill_before_service(self):
        service = SimpleNamespace(start=AsyncMock())
        fake_context = SimpleNamespace(
            user=SimpleNamespace(telegram_id=123456)
        )

        with patch(
            "app.api.ios_practice.DesktopAuthService.authenticate",
            new=AsyncMock(return_value=fake_context),
        ):
            async with await self._client(service) as client:
                response = await client.post(
                    "/api/v3/ios/practice/start",
                    headers={"Authorization": "Bearer access-token"},
                    json={
                        "mode": "training",
                        "level": "hsk2",
                        "language": "tj",
                        "skill": "unknown",
                    },
                )

        self.assertEqual(422, response.status_code)
        service.start.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
