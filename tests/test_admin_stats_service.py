import unittest

from app.services.admin_stats_service import miniapp_course_mode_stats_text


class _ScalarResult:
    def __init__(self, value: int):
        self.value = value

    def scalar(self) -> int:
        return self.value


class _Session:
    def __init__(self, value: int):
        self.value = value

    async def execute(self, _stmt):
        return _ScalarResult(self.value)


class AdminStatsServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_miniapp_course_mode_stats_text_shows_only_course_mode_count(self):
        text = await miniapp_course_mode_stats_text(_Session(12))

        self.assertIn("Mini App kurs rejimidagi foydalanuvchilar", text)
        self.assertIn("<b>12</b>", text)


if __name__ == "__main__":
    unittest.main()
