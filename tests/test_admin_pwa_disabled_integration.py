"""Flag-OFF main integration: no PWA DB work or legacy auth crossover."""
import unittest
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from tests import test_main_imports as main_imports


def pwa_routes(routes):
    for route in routes:
        path = getattr(route, 'path', '')
        if path == '/admin' or path.startswith(('/admin/', '/api/admin/v1/')):
            yield route
        nested = getattr(route, 'routes', None)
        if nested is None:
            nested = getattr(getattr(route, 'original_router', None), 'routes', [])
        yield from pwa_routes(nested or [])


class AdminPwaDisabledIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_every_mounted_pwa_entry_is_hidden_before_any_database_work(self):
        main = main_imports.MainModuleImportTests._import_main()
        routes = list(pwa_routes(main.app.routes))
        self.assertTrue(routes)
        with patch.object(main.settings, 'ADMIN_PWA_ENABLED', False), patch.object(
            type(main.async_session_maker), '__call__', side_effect=AssertionError('flag-off DB access')
        ) as db_factory:
            async with AsyncClient(transport=ASGITransport(app=main.app), base_url='https://hskai.app',
                headers={'origin': 'https://hskai.app', 'x-telegram-init-data': 'forged'},
                cookies={ADMIN_PWA_COOKIE_NAME: 'S'*64}) as client:
                for route in routes:
                    path = route.path.replace('{filename}', 'app.js').replace('{payment_id}', '1')
                    for method in route.methods - {'OPTIONS', 'HEAD'}:
                        with self.subTest(path=path, method=method):
                            kwargs = {'json': {}} if method == 'POST' else {}
                            response = await client.request(method, path, **kwargs)
                            self.assertEqual(response.status_code, 404, response.text)
                            self.assertEqual(response.headers['cache-control'], 'no-store')
                            self.assertNotIn('set-cookie', response.headers)
            db_factory.assert_not_called()

    async def test_pwa_cookie_cannot_authorize_existing_telegram_admin_routes(self):
        main = main_imports.MainModuleImportTests._import_main()
        # Test both rollout settings. Telegram auth remains independently required.
        for enabled in (False, True):
            with patch.object(main.settings, 'ADMIN_PWA_ENABLED', enabled), patch.object(
                type(main.async_session_maker), '__call__', side_effect=AssertionError('unauthorized DB access')
            ) as db_factory:
                async with AsyncClient(transport=ASGITransport(app=main.app), base_url='https://hskai.app',
                    cookies={ADMIN_PWA_COOKIE_NAME: 'S'*64}) as client:
                    for path, body in (
                        ('overview', {}), ('users/search', {'query': '1'}),
                        ('payments/review', {'payment_id': 1, 'action': 'approve'}),
                        ('users/delete', {'user_id': 1}), ('broadcast/send', {'text': 'synthetic QA'}),
                    ):
                        with self.subTest(path=path, enabled=enabled):
                            response = await client.post('/api/admin-miniapp/'+path, json=body)
                            self.assertEqual(response.status_code, 401, response.text)
                db_factory.assert_not_called()
