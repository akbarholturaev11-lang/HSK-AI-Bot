"""First-party OAuth consent screen: UX, strict CSRF, redirect and kill-switch.

Services are mocked; consent service itself has separate DB-backed tests.
No real Google, ChatGPT, payment or production access is involved.
"""
import re
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlencode, parse_qs, urlsplit
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.pwa_mcp_consent_transport import create_admin_pwa_mcp_consent_router
from app.admin_api.pwa_mcp_oauth import ApprovedMcpCode, DeniedMcpCode

ORIGIN="https://hskai.app"
CLIENT="registered-mcp-client"
REDIRECT="https://client.example/callback?fixed=1"
COOKIE="C"*64
REQUEST_ID="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
CSRF="s"*64
STATE="state-"+"u"*44
FORM={"request_id":REQUEST_ID,"csrf":CSRF,"decision":"allow"}
AUTH={
    "response_type":"code", "client_id":CLIENT, "redirect_uri":REDIRECT,
    "scope":"admin:analytics:read", "resource":ORIGIN+"/mcp",
    "state":STATE,"code_challenge":"z"*43,"code_challenge_method":"S256",
}


@asynccontextmanager
async def db():
    yield object()


class McpConsentTransportTests(unittest.TestCase):
    def setUp(self):
        self.settings=SimpleNamespace(
            ADMIN_PWA_ENABLED=True, ADMIN_PWA_MCP_ENABLED=True,
            ADMIN_PWA_MCP_TRANSPORT_ENABLED=True,
            ADMIN_PWA_MCP_RESOURCE=ORIGIN+"/mcp",
            ADMIN_PWA_MCP_CLIENT_ID=CLIENT, ADMIN_PWA_MCP_REDIRECT_URI=REDIRECT,
        )
        self.calls=[]
        async def begin(session, **kwargs):
            self.calls.append(("begin",kwargs))
            if kwargs.get("session_cookie")!=COOKIE:return None
            return SimpleNamespace(
                client_id=kwargs["client_id"], redirect_uri=kwargs["redirect_uri"],
                request_id=REQUEST_ID, csrf_proof=CSRF,
            )
        async def decide(session, **kwargs):
            self.calls.append(("decide",kwargs))
            if (kwargs["session_cookie"]!=COOKIE
                    or kwargs["request_id"]!=REQUEST_ID
                    or kwargs["csrf_proof"]!=CSRF):
                return None
            if kwargs["approved"]:
                return ApprovedMcpCode("Q"*64,REDIRECT,STATE,
                                       datetime.now(timezone.utc)+timedelta(seconds=60))
            return DeniedMcpCode(REDIRECT,STATE)
        app=FastAPI()
        app.include_router(create_admin_pwa_mcp_consent_router(
            settings_obj=self.settings,session_factory=db,
            begin_service=begin,decide_service=decide,
        ))
        self.client=TestClient(app,base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def get(self, *, params=None, cookie=True):
        return self.client.get("/oauth/authorize",params=AUTH if params is None else params,
                               headers={"cookie":"__Host-hskai_admin="+COOKIE} if cookie else {})

    def post(self, *, form=None, headers=None, cookie=True):
        h={"origin":ORIGIN,"sec-fetch-site":"same-origin",
           "content-type":"application/x-www-form-urlencoded"}
        if cookie:h["cookie"]="__Host-hskai_admin="+COOKIE
        if headers:h.update(headers)
        return self.client.post("/oauth/authorize",content=urlencode(FORM if form is None else form),
                                headers=h,follow_redirects=False)

    def test_mobile_first_accessible_page_and_no_authorization_code_on_get(self):
        r=self.get()
        self.assertEqual(r.status_code,200)
        self.assertIn('<h1 id="consent-title"',r.text)
        self.assertIn('name="decision" value="allow"',r.text)
        self.assertIn('name="decision" value="deny"',r.text)
        self.assertIn('name="request_id" value="'+REQUEST_ID+'"',r.text)
        self.assertIn('name="csrf" value="',r.text)
        self.assertIn("mcp-consent.css",r.text)
        self.assertIn("mcp-consent.js",r.text)
        self.assertIn("catalog.js",r.text)
        self.assertIn("width=device-width",r.text)
        self.assertIn(CLIENT,r.text)
        self.assertIn("client.example",r.text)
        self.assertNotIn(STATE,r.text)
        self.assertNotIn("code=",r.text)
        self.assertNotIn("access_token",r.text)
        self.assertEqual(r.headers["cache-control"],"no-store")
        self.assertIn("frame-ancestors 'none'",r.headers["content-security-policy"])
        self.assertIn("form-action 'self'",r.headers["content-security-policy"])
        self.assertFalse(r.headers.get_list("set-cookie"))
        self.assertEqual(len(self.calls),1)
        self.assertIn('name="csrf" value="'+CSRF+'"',r.text)

    def test_approve_redirects_only_to_exact_registered_uri_and_state(self):
        r=self.post()
        self.assertEqual(r.status_code,303)
        target=urlsplit(r.headers["location"])
        self.assertEqual(target.netloc,"client.example")
        self.assertEqual(target.scheme,"https")
        self.assertEqual(target.path,"/callback")
        q=parse_qs(target.query)
        self.assertEqual(q["fixed"],["1"])
        self.assertEqual(q["code"],["Q"*64])
        self.assertEqual(q["state"],[STATE])
        self.assertNotIn("access_token",str(q))
        self.assertEqual(r.headers["cache-control"],"no-store")
        self.assertEqual(self.calls[-1][1]["approved"],True)

    def test_deny_returns_only_standard_oauth_access_denied(self):
        r=self.post(form={**FORM,"decision":"deny"})
        self.assertEqual(r.status_code,303)
        q=parse_qs(urlsplit(r.headers["location"]).query)
        self.assertEqual(q["error"],["access_denied"])
        self.assertEqual(q["state"],[STATE])
        self.assertNotIn("code",q)
        self.assertFalse(r.headers.get_list("set-cookie"))

    def test_wrong_csrf_origin_fetchsite_session_are_denied(self):
        for form,head,cookie in [
            ({**FORM,"csrf":"bad"},{},True),
            (FORM,{"origin":"https://evil.example"},True),
            (FORM,{"origin":""},True),
            (FORM,{"sec-fetch-site":"cross-site"},True),
            (FORM,{"sec-fetch-site":"none"},True),
            (FORM,{},False),
        ]:
            with self.subTest(form=form,headers=head,cookie=cookie):
                self.assertIn(self.post(form=form,headers=head,cookie=cookie).status_code,
                              (400,401,403))
        # No client redirect in denied responses.
        self.assertFalse(self.post(headers={"origin":"https://evil.example"}).is_redirect)

    def test_duplicate_get_params_or_external_callback_never_redirect(self):
        for params in [
            list(AUTH.items())+[("client_id","evil")],
            {**AUTH,"redirect_uri":"https://evil.example/callback"},
            {**AUTH,"scope":"admin:payments:write"},
            {**AUTH,"code_challenge_method":"plain"},
            {**AUTH,"response_type":"token"},
            {**AUTH,"state":"short"},
            {k:v for k,v in AUTH.items() if k!="resource"},
        ]:
            with self.subTest(params=params):
                self.assertIn(self.get(params=params).status_code,(400,403))
        self.assertFalse(self.get(params={**AUTH,"redirect_uri":"https://evil.example/"}).is_redirect)

    def test_all_feature_flags_keep_consent_inactive(self):
        for flag in ("ADMIN_PWA_ENABLED","ADMIN_PWA_MCP_ENABLED",
                     "ADMIN_PWA_MCP_TRANSPORT_ENABLED"):
            setattr(self.settings,flag,False)
            self.assertEqual(self.get().status_code,404)
            self.assertEqual(self.post().status_code,404)
            setattr(self.settings,flag,True)
        self.assertEqual(self.get(cookie=False).status_code,401)

    def test_post_rejects_unknown_fields_duplicate_and_bad_media(self):
        for form in [
            {**FORM,"actor_id":"1"},
            {**FORM,"decision":"execute"},
            {**FORM,"request_id":""},
        ]:
            self.assertIn(self.post(form=form).status_code,(400,403))
        self.assertEqual(self.post(headers={"content-type":"application/json"}).status_code,400)

    def test_html_substitution_escapes_registered_client(self):
        # Server-configured client names are escaped even if config itself
        # were accidentally polluted with HTML special characters.
        self.settings.ADMIN_PWA_MCP_CLIENT_ID='bad<script>alert(1)</script>'
        new_auth={**AUTH,"client_id":self.settings.ADMIN_PWA_MCP_CLIENT_ID}
        r=self.get(params=new_auth)
        self.assertEqual(r.status_code,200)
        self.assertIn("bad&lt;script&gt;",r.text)
        self.assertNotIn("bad<script>",r.text)


if __name__=="__main__":
    unittest.main()
