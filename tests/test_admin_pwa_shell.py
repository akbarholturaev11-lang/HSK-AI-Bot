"""Public-only shell contract. No provider/device/live account claims."""
import unittest
from types import SimpleNamespace
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from app.admin_api.pwa_bootstrap import create_admin_pwa_bootstrap_router


class AdminPwaShellTests(unittest.IsolatedAsyncioTestCase):
    async def get(self, path, enabled=True, base='https://hskai.app'):
        app=FastAPI()
        app.include_router(create_admin_pwa_bootstrap_router(settings_obj=SimpleNamespace(
            ADMIN_PWA_ENABLED=enabled, ADMIN_PWA_PUBLIC_ORIGIN='https://hskai.app')))
        async with AsyncClient(transport=ASGITransport(app=app),base_url=base) as client:
            return await client.get(path)

    async def test_all_entries_fail_closed_and_legacy_route_is_absent(self):
        for path in ('/admin','/admin/','/admin/manifest.webmanifest','/admin/sw.js',
                     '/admin/assets/app.js','/admin/assets/catalog.js','/admin/assets/icon-large.png'):
            self.assertEqual((await self.get(path,False)).status_code,404,path)
            self.assertEqual((await self.get(path,base='http://hskai.app')).status_code,403,path)
        self.assertEqual((await self.get('/admin.html')).status_code,404)
        self.assertEqual((await self.get('/admin/assets/unknown.js')).status_code,404)

    async def test_public_shell_strict_csp_and_fixed_redirect(self):
        redirect=await self.get('/admin')
        self.assertEqual((redirect.status_code,redirect.headers['location']),(303,'/admin/'))
        shell=await self.get('/admin/')
        self.assertEqual(shell.status_code,200)
        self.assertEqual(shell.headers['cache-control'],'no-store')
        self.assertNotIn('unsafe-inline',shell.headers['content-security-policy'])
        self.assertNotIn('set-cookie',shell.headers)
        self.assertIn('src="/admin/assets/app.js"',shell.text)
        self.assertNotIn('v6Demo',shell.text)
        self.assertNotIn('user_id',shell.text)

    async def test_apple_push_subscription_keeps_user_activation_on_direct_tap(self):
        # The public script can offer push settings only after the server
        # advertises the private feature. No permission prompt at boot/login.
        script=(await self.get('/admin/assets/app.js')).text
        self.assertIn("state.actor?.push_available",script)
        self.assertIn("pushReady={registration,key:decode(data.vapid_public_key)",script)
        opt_in=script.split("async function enablePush(){",1)[1].split("async function revokePush",1)[0]
        self.assertIn("pushManager.subscribe({",opt_in)
        self.assertNotIn("Notification.requestPermission()",opt_in)
        # On iPhone an async fetch/getSubscription before subscribe would lose
        # the direct user gesture and can silently prevent enrollment.
        self.assertLess(opt_in.index("pushManager.subscribe({"),
                        opt_in.index("await subscriptionPromise"))
        self.assertNotIn("await api('push/list'",opt_in)
        self.assertIn("Notification.permission==='denied'",opt_in)
        self.assertIn("if(!prepared.previous)await subscription.unsubscribe()",opt_in)
        self.assertIn("pushChanging=true",opt_in)

    async def test_apple_push_settings_respect_sender_readiness(self):
        # Enrollment readiness does not mean delivery. The server controls
        # sender readiness, so the old 'not sending' warning applies only
        # when the API says the opt-in dispatcher is not configured.
        script=(await self.get('/admin/assets/app.js')).text
        settings_ui=script.split('async function pushSettings(){',1)[1].split('async function enablePush(){',1)[0]
        self.assertIn("data.sending_enabled===true?'':", settings_ui)
        self.assertIn("t('pushNotSending')", settings_ui)
        self.assertIn('${deliveryNote}${devices}', settings_ui)
        self.assertNotIn("</p><p class=\"source-note\">${esc(t('pushNotSending'))}</p>${devices}", settings_ui)
        # The actual Web Push provider and physical Apple delivery are not
        # exercised by this public-shell regression.

    async def test_inbox_search_form_is_private_and_bounded(self):
        script=(await self.get('/admin/assets/app.js')).text
        self.assertIn('id="inboxSearchForm"', script)
        self.assertIn('id="inboxSearchQuery"', script)
        self.assertIn('minlength="3" maxlength="80"', script)
        self.assertIn("search:state.inboxSearch||null", script)
        self.assertIn("state.inboxSearch='';state.actor=null", script)
        self.assertIn("state.inboxSearch=value", script)
        self.assertIn("t('monthly')", script)
        self.assertNotIn("localStorage.setItem('hsk-admin-inbox-search'", script)

    async def test_worker_scope_version_and_public_cache_allowlist(self):
        manifest=(await self.get('/admin/manifest.webmanifest')).json()
        self.assertEqual(manifest['scope'],'/admin/')
        self.assertEqual(manifest['start_url'],'/admin/')
        worker=await self.get('/admin/sw.js')
        self.assertEqual(worker.headers['service-worker-allowed'],'/admin/')
        self.assertNotIn('__SHELL_VERSION__',worker.text)
        self.assertIn('!PUBLIC.includes(url.pathname)',worker.text)
        self.assertIn('url.search',worker.text)
        self.assertNotIn("'/api/",worker.text)
        # Apple Web Push must always show a visible generic notification,
        # ignore all untrusted push payload, never access private API/cache,
        # and navigate only to a fixed first-party inbox URL.
        self.assertIn("self.addEventListener('push'", worker.text)
        self.assertIn("self.registration.showNotification", worker.text)
        self.assertIn("self.addEventListener('notificationclick'", worker.text)
        self.assertIn("'/admin/?inbox=1'", worker.text)
        self.assertIn("current.pathname === '/admin/'", worker.text)
        push_handler = worker.text.split("self.addEventListener(\'push\'", 1)[1].split("self.addEventListener(\'notificationclick\'", 1)[0]
        self.assertNotIn("event.data", push_handler)
        self.assertNotIn("pushSubscription", worker.text)
        for filename in ('app.js','styles.css','catalog.js','icon.png','icon-large.png'):
            response=await self.get('/admin/assets/'+filename)
            self.assertEqual(response.status_code,200,filename)
            self.assertNotIn('set-cookie',response.headers)
