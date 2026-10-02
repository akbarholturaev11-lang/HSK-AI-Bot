import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.admin_broadcast_service import (
    AdminBroadcastService,
    parse_broadcast_filters,
)


class AdminBroadcastHskTrackTests(unittest.IsolatedAsyncioTestCase):
    def test_parse_accepts_only_known_course_tracks(self):
        hsk30 = parse_broadcast_filters({"track": "hsk30", "level": "nhsk1"})
        invalid = parse_broadcast_filters({"track": "hsk99"})

        self.assertEqual(hsk30["track"], "hsk30")
        self.assertEqual(hsk30["level"], "nhsk1")
        self.assertIsNone(invalid["track"])

    async def test_target_users_forwards_course_track_to_repository(self):
        session = SimpleNamespace()
        service = AdminBroadcastService(SimpleNamespace(), session)
        users = [SimpleNamespace(telegram_id=700, level="nhsk1")]

        with patch(
            "app.services.admin_broadcast_service.UserRepository.get_filtered_users",
            new=AsyncMock(return_value=users),
        ) as filtered:
            result = await service.target_users(
                parse_broadcast_filters(
                    {
                        "track": "hsk30",
                        "level": "nhsk1",
                        "status": "active",
                    }
                )
            )

        self.assertEqual(result, users)
        filtered.assert_awaited_once()
        kwargs = filtered.await_args.kwargs
        self.assertEqual(kwargs["course_track"], "hsk30")
        self.assertEqual(kwargs["level"], "nhsk1")
        self.assertEqual(kwargs["status"], "active")


if __name__ == "__main__":
    unittest.main()
