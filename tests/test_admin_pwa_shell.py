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


    async def test_confirmed_limits_save_reconciles_visible_draft_before_refresh(self):
        script = (await self.get('/admin/assets/app.js')).text
        self.assertIn("const committed=await api('limits/save'", script)
        self.assertIn("courseData.limits=committed.limits;", script)
        self.assertIn('if(!courseLimitTouched[courseLimitPlan])return false;',script)
        self.assertIn('courseLimitTouched={FREE:false,TRIAL_ACTIVE:false}',script)
        self.assertIn("courseLimitDraft={FREE:structuredClone(committed.limits.plans.FREE)", script)
        self.assertIn("courseTrialDraft={enabled:committed.limits.trial.enabled", script)
        self.assertIn("confirmation=null;showSavedAndDismiss('changesSaved');void loadCourseData();", script)

    async def test_user_directory_seven_column_visual_contract(self):
        script = (await self.get('/admin/assets/app.js')).text
        stylesheet = (await self.get('/admin/assets/styles.css')).text
        catalog = (await self.get('/admin/assets/catalog.js')).text
        self.assertIn("['directoryUserTariff','directoryAge','language','level','directoryPlanMethod','lastActive','status']", script)
        self.assertIn('function accountAge(value,clock=Date.now())', script)
        self.assertIn('userPaymentMethod(userDirectoryMethod(row))', script)
        self.assertIn('userSelectedDuration(userDirectoryPlan(row))', script)
        self.assertIn("row.access_state==='PRO_ACTIVE'?row.last_approved_plan_type:null",script)
        self.assertIn("row.access_state==='PRO_ACTIVE'?row.last_approved_payment_method:null",script)
        self.assertIn('userPlanMethod(row)', script)
        self.assertIn("if(row.access_state==='TRIAL_ACTIVE')return 'Pro trial';", script)
        self.assertIn("type==='PRO_ACTIVE'||type==='TEMP_ACCESS'?'blue':'gray'", script)
        self.assertIn("esc(row.name||'—')", script)
        self.assertIn('.user-status-pill{', stylesheet)
        self.assertIn('.pill.user-status-pill.blue:not(.green):not(.red):not(.amber):not(.gray){', stylesheet)
        self.assertIn('.user-table{min-width:1020px;table-layout:fixed}', stylesheet)
        self.assertIn('"directoryUserTariff":"Фойдаланувчи / тариф"', catalog)
        self.assertIn('"directoryPlan1Month":"1 ой"', catalog)

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

    async def test_minimal_inbox_and_seamless_passkey_launch_contract(self):
        script=(await self.get('/admin/assets/app.js')).text
        list_section=script.split('async function inbox(before=null,userId=null)',1)[1].split('async function mutateInbox(',1)[0]
        self.assertNotIn('inboxSearchForm',list_section)
        self.assertNotIn('filterSelect',list_section)
        self.assertNotIn('inboxHistoryNote',list_section)
        self.assertIn('data.items.map(inboxEntry)',list_section)
        self.assertIn("operation:'mark_read'",script)
        self.assertIn('data-inbox-open',script)
        self.assertIn("if(source==='payment'){",script)
        self.assertIn("await review(id);",script)
        self.assertIn("drawerBack=()=>inbox(null,originatingUser)",script)
        self.assertIn("if(state.phase==='signin')await tryAutomaticPasskeyLogin();",script)
        self.assertIn("await api('me',null,{method:'GET',publicAuth:true})",script)
        self.assertIn("lockAndRequirePasskey();",script)
        self.assertIn("await api('auth/logout',{}, {publicAuth:true})",script)
        self.assertIn("resumeAuthenticationRequired=true",script)
        self.assertIn("if(biometricPromptInProgress||signing)return;",script)
        self.assertIn("credential=await navigator.credentials.get(",script)
        self.assertIn("await api('auth/passkey/login/verify'",script)

    async def test_iphone_full_width_swipe_is_single_step_and_input_safe(self):
        script=(await self.get('/admin/assets/app.js')).text
        start=script.index('function canSwipeBack(target) {')
        end=script.index("document.addEventListener('click',event=>{",start)
        self.assertGreaterEqual(start,0)
        gesture=script[start:end]
        self.assertIn("document.addEventListener('touchstart'",gesture)
        self.assertIn("document.addEventListener('touchend'",gesture)
        self.assertIn("document.addEventListener('touchcancel'",gesture)
        self.assertIn("document.addEventListener('touchmove'",gesture)
        self.assertIn("swipePreview(dx)",gesture)
        self.assertIn("await animateBack()",gesture)
        self.assertNotIn("touch.clientX>window.innerWidth*0.30",gesture)
        self.assertIn("if(dx<78",gesture)
        self.assertIn("event.touches.length!==1",gesture)
        self.assertIn("touch.identifier!==start.id",gesture)
        self.assertIn("getComputedStyle(node).overflowX",gesture)
        self.assertIn("input,textarea,select,[contenteditable]",gesture)
        self.assertIn("signing||inboxUpdating",gesture)
        self.assertIn("if(!standalone&&touch.clientX<24)return;",gesture)
        self.assertIn("oneStepBack().catch",gesture)
        self.assertIn("event.stopImmediatePropagation()",script)
        self.assertIn("const previous=drawerBack",gesture)
        self.assertIn("sectionBackStack.pop()",gesture)
        self.assertIn("if(source==='payment'){",script)
        self.assertIn("drawerBack=()=>inbox(null,originatingUser)",script)
        # Payment decisions stay in their original editor and keep the Inbox
        # return target; there is no extra confirmation layer to navigate back.
        self.assertNotIn("drawer('confirmPayment'",script)
        # The gesture must not turn into browser history navigation.
        self.assertNotIn("history.back()",gesture)
        self.assertNotIn("location.assign(",gesture)


    async def test_all_editors_have_single_dirty_save_and_short_success_feedback(self):
        script=(await self.get('/admin/assets/app.js')).text
        stylesheet=(await self.get('/admin/assets/styles.css')).text
        # The top-right X is the cancel action, even on iPhone.
        self.assertNotIn("btn('cancel','close')",script)
        self.assertNotIn("btn('cancel','priceSettings')",script)
        self.assertIn("editorBaseline={panel,value:editorValue()}",script)
        self.assertIn("function updateEditorSaveEnabled(){",script)
        self.assertIn("b.disabled=!dirty||requiresProof||managementPreparing||!!signing",script)
        self.assertIn("function showSavedAndDismiss(key='changesSaved'){",script)
        self.assertIn("role=\"status\"",script)
        self.assertIn("},2500)",script)
        self.assertIn(".saved-tick{",stylesheet)
        self.assertIn(".swipe-back-cue",stylesheet)
        # Transaction-bound WebAuthn still gates all confirmed writes.
        self.assertIn("await api('auth/step-up/verify'",script)
        self.assertIn("await api(managementEndpoint(review.type,'save'),command)",script)

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
