from contextlib import asynccontextmanager
import unittest
from unittest.mock import AsyncMock, patch

from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService


class FakeSession:
    def __init__(self):
        self.events = []

    @asynccontextmanager
    async def begin_nested(self):
        yield

    def add(self, event):
        self.events.append(event)

    async def flush(self):
        pass


class ActivityTests(unittest.IsolatedAsyncioTestCase):
    async def test_passive_events_do_not_touch_activity(self):
        session = FakeSession()
        service = CourseMiniAppAnalyticsService(session)
        with patch.object(service, '_touch_user_active', new_callable=AsyncMock) as touch:
            for event in ('subscription_approved', 'd1_recovery_sent', 'sales_offer_assigned'):
                result = await service.record_server_event(event_name=event, user_id=42)
                self.assertTrue(result['recorded'])
            touch.assert_not_awaited()
        self.assertEqual(len(session.events), 3)

    async def test_real_activity_is_still_touched(self):
        service = CourseMiniAppAnalyticsService(FakeSession())
        with patch.object(service, '_touch_user_active', new_callable=AsyncMock) as touch:
            for event in ('lesson_started', 'miniapp_opened', 'android_app_opened'):
                result = await service.record_server_event(event_name=event, user_id=42)
                self.assertTrue(result['recorded'])
            self.assertEqual(touch.await_count, 3)


if __name__ == '__main__':
    unittest.main()
