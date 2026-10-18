"""The real HTTP app must serve the pinned SDK used by the onboarding pages."""
import hashlib
from pathlib import Path
import unittest

import httpx


class TelegramSdkAssetTests(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_is_public_and_returns_the_pinned_official_bytes(self):
        from app.main import app
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get('/assets/telegram-web-app.js?v=20261019-1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/javascript', response.headers['content-type'])
        self.assertEqual(response.content, Path('app/static/assets/telegram-web-app.js').read_bytes())
        self.assertEqual(hashlib.sha256(response.content).hexdigest(),
                         '124bdff7ba3fe86c8ba5143467afec21e020405e74abdb92cfdda6c0ee3b5908')
