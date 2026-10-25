"""Course policy reads accept only the bounded empty-object contract."""
import unittest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.admin_api.pwa_course_access import create_admin_pwa_course_access_router
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from tests import test_admin_pwa_payment_review as fixtures


class CoursePolicyTransportTests(fixtures.PaymentFixtures, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AdminPwaPaymentReviewTests.asyncSetUp
    asyncTearDown = fixtures.AdminPwaPaymentReviewTests.asyncTearDown

    async def test_read_rejects_unknown_duplicate_malformed_and_oversized_body(self):
        app = FastAPI()
        app.include_router(create_admin_pwa_course_access_router(settings_obj=self.settings,
                                                               session_factory=self.sessions))
        async with AsyncClient(transport=ASGITransport(app=app), base_url='https://hskai.app',
                headers={'origin':'https://hskai.app','content-type':'application/json'},
                cookies={ADMIN_PWA_COOKIE_NAME:fixtures.COOKIE}) as client:
            for raw in ('[]','null','{"mode":"subscription"}','{"a":1,"a":2}','{invalid',' '*2049):
                self.assertEqual((await client.post('/api/admin/v1/course-access/read',content=raw)).status_code,400)
            response=await client.post('/api/admin/v1/course-access/read',json={})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertEqual(response.json()['course_access']['mode'],'subscription')
