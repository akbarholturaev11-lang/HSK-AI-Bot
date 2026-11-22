"""Diagnostic precision (tasks 6.1-6.4): allowlisted debug evidence only.

Contract and security checks need no database. The PostgreSQL class drives
the verified PWA cookie + CSRF intake into real receipts and the authenticated
Admin Inbox, then checks that nothing a learner could type or a forged client
could send reaches the database, the Admin API, the push outbox or the logs.
"""
import hashlib
import importlib.util
import json
import logging
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, inspect, select, text

import tests.test_pwa_browser_auth as pwa
from app.api.monitoring_intake import create_monitoring_intake_router
from app.api.pwa_auth import create_pwa_auth_router
from app.db.base import Base
from app.db.models.admin_pwa_push_outbox import AdminPwaPushOutbox
from app.db.models.desktop import DesktopLinkRequest
from app.db.models.diagnostic import DiagnosticIncident, DiagnosticReceipt
from app.repositories.user_repo import UserRepository
from app.services.monitoring import catalog, source
from app.services.monitoring.intake import IntakeRejected, fingerprint, ingest, parse_batch
from app.services.monitoring.retention import purge_diagnostics
from app.services.pwa_auth_service import PWA_SESSION_COOKIE, PwaAuthService
from scripts.i18n_baseline_guard import git_blob_sha1
from tests.monitoring_chain import PG_URL, admin_client, client_event, pg_sessions

ROOT = Path(__file__).resolve().parents[1]
REPORTER = ROOT / "app/static/course_v3_data/hsk-diagnostics.js"
MIGRATION = ROOT / "alembic/versions/0157_diagnostic_precision.py"
INTAKE = "/api/v3/pwa/diagnostics"
LIST = "/api/admin/v1/inbox/list"
TRIAGE = "/api/admin/v1/inbox/triage"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
HANDOFF = "iphone_pwa_handoff"
# Strings a forged client or a learner's page could try to smuggle.
SECRETS = ("secretProp", "evilFn", "hsk.test", "token=abc", "learner@example.com", "initData",
           "Cannot read properties", "<script", "../")


def blob_token(asset_id):
    return git_blob_sha1((ROOT / catalog.DEBUG_ASSETS[asset_id]).read_bytes())[:12]


def js_event(platform="iphone_pwa", failure="js_uncaught", **debug):
    """A learner-web JS failure with a category, plus the given debug fields."""
    return client_event("distribution_handoff", failure, "pwa_handoff", platform, **{"category": "type", **debug})


def place(asset_id=HANDOFF, line=57, column=9, **extra):
    return {"asset_id": asset_id, "line": line, "column": column, **extra}


def parse(*events, platform="iphone_pwa"):
    return parse_batch({"schema": "diag.v1", "events": list(events)}, platform=platform)


class ContractTests(unittest.TestCase):
    def test_complete_debug_evidence_is_accepted_for_web_js_failures(self):
        for platform in ("iphone_pwa", "telegram"):
            for failure in ("js_uncaught", "js_rejection"):
                frames = [place("li_onboarding_install", 120 + n, 14, asset_version="b32fe2d0770a") for n in range(5)]
                events, rejected = parse(js_event(platform, failure, error_name="TypeError",
                                                  reason_code="null_access", location=place(), frames=frames),
                                         platform=platform)
                self.assertEqual(rejected, 0)
                event, = events
                self.assertEqual((event.error_name, event.reason_code), ("TypeError", "null_access"))
                self.assertEqual(event.locations[0], (HANDOFF, 57, 9, None))
                self.assertEqual(event.locations[5], ("li_onboarding_install", 124, 14, "b32fe2d0770a"))
                self.assertEqual(len(event.locations), 6)
        events, _ = parse(js_event(location={"asset_id": HANDOFF, "line": 1}))
        self.assertEqual(events[0].locations, ((HANDOFF, 1, None, None),))
        events, _ = parse(js_event(error_name="Error", category="other"))
        self.assertEqual((events[0].error_name, events[0].locations), ("Error", ()))

    def test_a_plain_v1_event_is_unchanged(self):
        events, rejected = parse(js_event())
        self.assertEqual((rejected, events[0].error_name, events[0].reason_code, events[0].locations),
                         (0, None, None, ()))

    def test_raw_text_keys_reject_the_whole_request(self):
        # There is no key a message, stack, URL or function name could use.
        for key in ("message", "stack", "filename", "url", "href", "function", "function_name", "source",
                    "cause", "error", "path", "query", "fragment", "token", "initData", "cookie", "user_id"):
            for bad in (js_event(**{key: "private"}), js_event(location=place(**{key: "private"})),
                        js_event(location=place(), frames=[place(**{key: "private"})])):
                with self.subTest(key=key), self.assertRaises(IntakeRejected) as caught:
                    parse(js_event(), bad)
                self.assertEqual(caught.exception.code, "forbidden_field")

    def test_forged_or_malformed_debug_values_reject_only_that_event(self):
        ok = dict(error_name="TypeError", reason_code="null_access", location=place())
        long_frames = [place(line=n + 1) for n in range(catalog.MAX_FRAMES + 1)]
        bad_values = {
            "unknown asset": {"location": place("admin_app")},
            "path traversal": {"location": place("../../etc/passwd")},
            "repository path": {"location": place("app/static/iphone-pwa-handoff.js")},
            "absolute URL": {"location": place("https://hsk.test/iphone-pwa-handoff.js?token=abc")},
            "query on the id": {"location": place(HANDOFF + "?v=1")},
            "PII as asset": {"location": place("learner@example.com")},
            "asset not a string": {"location": place(["iphone_pwa_handoff"])},
            "location not an object": {"location": "iphone_pwa_handoff:57:9"},
            "location null": {"location": None},
            "line zero": {"location": place(line=0)},
            "line negative": {"location": place(line=-5)},
            "line overflow": {"location": place(line=catalog.MAX_SOURCE_LINE + 1)},
            "line huge": {"location": place(line=2 ** 63)},
            "line float": {"location": place(line=57.0)},
            "line bool": {"location": place(line=True)},
            "line string": {"location": place(line="57")},
            "line missing": {"location": {"asset_id": HANDOFF}},
            "column zero": {"location": place(column=0)},
            "column negative": {"location": place(column=-1)},
            "column overflow": {"location": place(column=catalog.MAX_SOURCE_COLUMN + 1)},
            "column string": {"location": place(column="9")},
            "version too long": {"location": place(asset_version="0123456789abc")},
            "version uppercase": {"location": place(asset_version="0123456789AB")},
            "version with a date": {"location": place(asset_version="20261114-abcd")},
            "version with a query": {"location": place(asset_version="abc?token=x")},
            "version not a string": {"location": place(asset_version=123456789012)},
            "too many frames": {"frames": long_frames},
            "frames without a location": {"location": ..., "frames": [place()]},
            "empty frames": {"frames": []},
            "frames not a list": {"frames": {"0": place()}},
            "frame is text": {"frames": ["evilFn@https://hsk.test/a.js:1:1"]},
            "frame null": {"frames": [None]},
            "forged frame asset": {"frames": [place(), place("evil_cdn")]},
            "unknown name": {"error_name": "EvilError"},
            "markup as name": {"error_name": "<script>alert(1)</script>"},
            "message as name": {"error_name": "Cannot read properties of undefined (reading 'secretProp')"},
            "name of another category": {"error_name": "RangeError"},
            "name not a string": {"error_name": 7},
            "name null": {"error_name": None},
            "unknown reason": {"reason_code": "secretProp_is_null"},
            "reason of another exception": {"reason_code": "json_parse"},
            "reason not a string": {"reason_code": ["null_access"]},
            "reason without a name": {"error_name": ..., "reason_code": "null_access"},
        }
        for label, change in bad_values.items():
            fields = {key: value for key, value in {**ok, **change}.items() if value is not ...}
            with self.subTest(label):
                events, rejected = parse(js_event(), js_event(**fields))
                self.assertEqual((len(events), rejected), (1, 1))
                self.assertEqual(events[0].locations, ())

    def test_debug_evidence_is_limited_to_web_js_failures_with_a_category(self):
        debug = dict(error_name="TypeError", location=place())
        android = client_event("lessons", "crash_uncaught", "exc_null", "android", category="type", **debug)
        self.assertEqual(parse(android, platform="android"), ([], 1))
        handled = client_event("lessons", "load_failed", "lesson_open", "iphone_pwa", category="type", **debug)
        self.assertEqual(parse(handled), ([], 1))
        uncategorised = client_event("lessons", "js_uncaught", "course_v3", "iphone_pwa", **debug)
        self.assertEqual(parse(uncategorised), ([], 1))

    def test_exception_identity_groups_without_line_column_or_version(self):
        """NXT-011: name, reason and primary asset separate incidents on one page."""
        page = fingerprint("iphone_pwa", "distribution_handoff", "js_uncaught", "pwa_handoff")
        plain, = parse(js_event())[0]
        self.assertEqual(plain.fingerprint, page, "no evidence keeps the original page-level incident")
        rich, = parse(js_event(error_name="TypeError", reason_code="not_callable", location=place(line=999)))[0]
        moved, = parse(js_event(error_name="TypeError", reason_code="not_callable",
                                location=place(line=3, column=1, asset_version="0123456789ab"),
                                app_version="20261120-abcdef123456", build=20261120,
                                frames=[place("hsk_diagnostics", 5)]))[0]
        self.assertEqual(rich.fingerprint, moved.fingerprint, "a redeploy or another frame never splits one error")
        self.assertEqual(rich.fingerprint, fingerprint("iphone_pwa", "distribution_handoff", "js_uncaught",
                                                       "pwa_handoff", "e=TypeError|r=not_callable|a=" + HANDOFF))
        others = [
            js_event(error_name="TypeError", reason_code="null_access", location=place()),
            js_event(error_name="TypeError", reason_code="not_callable", location=place("hsk_diagnostics")),
            js_event(error_name="TypeError", reason_code="not_callable"),
            js_event(error_name="TypeError"),
            js_event(location=place()),
            js_event(error_name="RangeError", category="range", location=place()),
        ]
        prints = {rich.fingerprint, page} | {parse(event)[0][0].fingerprint for event in others}
        self.assertEqual(len(prints), len(others) + 2, "each distinct identity is its own incident")
        self.assertEqual(rich.identity, "e=TypeError|r=not_callable|a=" + HANDOFF)
        self.assertIsNone(plain.identity)

    def test_exception_identity_is_limited_to_web_js_failures(self):
        android = client_event("lessons", "crash_uncaught", "exc_null", "android", category="type")
        event, = parse(android, platform="android")[0]
        self.assertIsNone(event.identity)
        self.assertEqual(event.fingerprint, fingerprint("android", "lessons", "crash_uncaught", "exc_null"))
        telegram, = parse(js_event("telegram", error_name="TypeError", location=place()), platform="telegram")[0]
        self.assertEqual(telegram.identity, "e=TypeError|r=-|a=" + HANDOFF)
        rejection, = parse(js_event(failure="js_rejection", error_name="TypeError"))[0]
        self.assertEqual(rejection.fingerprint, fingerprint("iphone_pwa", "distribution_handoff", "js_rejection",
                                                            "pwa_handoff", "e=TypeError|r=-|a=-"))

    def test_severity_is_unchanged_by_debug_evidence(self):
        plain, = parse(js_event())[0]
        rich, = parse(js_event(error_name="TypeError", reason_code="not_callable", location=place()))[0]
        self.assertEqual(catalog.severity_for(plain.feature_code, plain.failure_code),
                         catalog.severity_for(rich.feature_code, rich.failure_code))

    def test_reporter_allowlists_mirror_the_server_catalog(self):
        script = REPORTER.read_text(encoding="utf-8")

        def literal(name, close):
            start = script.index("var " + name + " = ") + len("var " + name + " = ")
            body = script[start:script.index(close, start) + len(close) - 1]
            return json.loads(re.sub(r"(?m)([{,]\s*)([A-Za-z]+):", r'\1"\2":', body))

        files = literal("ASSET_FILES", "};")
        client = {name.replace("-", "_"): "app/static" + directory + name + ".js"
                  for directory, names in files.items() for name in names}
        self.assertEqual(client, catalog.DEBUG_ASSETS)
        self.assertEqual(len(client), sum(len(names) for names in files.values()), "an asset ID is never shared")
        for asset_id, path in catalog.DEBUG_ASSETS.items():
            with self.subTest(asset_id):
                self.assertRegex(asset_id, r"^[a-z][a-z0-9_]{0,47}$")
                self.assertRegex(path, r"^app/static/[A-Za-z0-9_./-]+\.js$")
                self.assertNotIn("..", path)
                self.assertTrue((ROOT / path).is_file())
                self.assertNotIn(".min.", path)
                self.assertNotIn("vendor", path)
        categories = literal("CATEGORIES", "};")
        names = {**categories, **dict.fromkeys(literal("EXTRA_NAMES", "];"), "other")}
        self.assertEqual(names, catalog.ERROR_NAMES)
        self.assertEqual(set(literal("REASONS", "];")), set(catalog.REASONS))
        self.assertLessEqual(set(catalog.ERROR_NAMES.values()), catalog.CATEGORIES)
        for allowed in catalog.REASONS.values():
            self.assertLessEqual(allowed, set(catalog.ERROR_NAMES))
        self.assertIn("var MAX_FRAMES = %d;" % catalog.MAX_FRAMES, script)
        self.assertIn("var MAX_POSITION = %d;" % catalog.MAX_SOURCE_LINE, script)

    def test_every_listed_asset_is_served_from_its_repository_file(self):
        import asyncio
        import app.main as main

        # The two sign-in page scripts live on the PWA router, which the
        # default test configuration keeps switched off.
        gated = FastAPI()
        gated.include_router(create_pwa_auth_router(session_factory=None, settings_obj=pwa.settings()))

        async def fetch():
            served = {}
            for application in (main.app, gated):
                async with AsyncClient(transport=ASGITransport(app=application), base_url="https://hsk.test") as client:
                    for asset_id, path in catalog.DEBUG_ASSETS.items():
                        if served.get(asset_id) is None or served[asset_id].status_code != 200:
                            served[asset_id] = await client.get(path.removeprefix("app/static"))
            return served

        served = asyncio.run(fetch())
        for asset_id, response in served.items():
            with self.subTest(asset_id):
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, (ROOT / catalog.DEBUG_ASSETS[asset_id]).read_bytes())

    def test_source_link_needs_a_verified_asset_and_an_exact_commit(self):
        raw = (ROOT / catalog.DEBUG_ASSETS[HANDOFF]).read_bytes()
        self.assertEqual(source.asset_tokens(HANDOFF),
                         {git_blob_sha1(raw)[:12], hashlib.sha256(raw).hexdigest()[:12]})
        self.assertTrue(source.is_deployed_version(HANDOFF, blob_token(HANDOFF)))
        for stale in (None, "", "0123456789ab", blob_token("voice_live")):
            self.assertFalse(source.is_deployed_version(HANDOFF, stale))
        self.assertFalse(source.is_deployed_version("unknown_asset", blob_token(HANDOFF)))
        self.assertEqual(source.source_url(COMMIT, HANDOFF, 57),
                         f"https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/{COMMIT}/"
                         "app/static/iphone-pwa-handoff.js#L57")
        # A `?v=` cache token, a short SHA, a branch name or a tag is never a commit.
        for commit in (None, "", "20261114-cde219a1e184", "cde219a1e184", COMMIT[:39], COMMIT + "0", COMMIT.upper(),
                       "main", "refs/heads/main", "v1.8.0"):
            self.assertIsNone(source.source_url(commit, HANDOFF, 57))
        for asset_id, line in (("unknown_asset", 57), (HANDOFF, 0), (HANDOFF, -1), (HANDOFF, "57"), (HANDOFF, True)):
            self.assertIsNone(source.source_url(COMMIT, asset_id, line))
        for value, expected in ((COMMIT, COMMIT), (COMMIT.upper(), COMMIT), ("", None), ("main", None),
                                ("20261114-cde219a1e184", None), (COMMIT[:12], None)):
            settings = pwa.settings(MONITORING_SOURCE_COMMIT=value)
            self.assertEqual(source.deployed_commit(settings), expected)
        self.assertIsNone(source.deployed_commit(pwa.settings()))

    def test_every_category_and_reason_is_localized_in_uz_ru_tj(self):
        labels = ("diagSample", "diagErrorName", "diagCategory", "diagReason", "diagLocation", "diagFrames",
                  "diagNotCaptured")
        keys = [*labels, *("diagCategory_" + code for code in catalog.CATEGORIES),
                *("diagReason_" + code for code in catalog.REASONS)]
        generated = (ROOT / "app/static/admin-pwa/catalog.js").read_text(encoding="utf-8")
        seen = {}
        for lang in ("uz", "ru", "tj"):
            copy = json.loads((ROOT / f"localization/ui/{lang}/miniapp.json").read_text(encoding="utf-8"))
            flat = json.dumps(copy, ensure_ascii=False)
            for key in keys:
                with self.subTest(lang=lang, key=key):
                    found = re.search(r'"ui\.admin_pwa\.%s": "([^"]+)"' % re.escape(key), flat)
                    self.assertIsNotNone(found)
                    self.assertTrue(found.group(1).strip())
                    self.assertIn(found.group(1), generated)
                    seen.setdefault(key, set()).add(found.group(1))
        # A reason is a general explanation; no copy claims a proven root cause.
        self.assertEqual(len(seen["diagReason"]), 3)

    def test_admin_page_renders_a_link_only_for_the_exact_github_blob_shape(self):
        app_js = (ROOT / "app/static/admin-pwa/app.js").read_text(encoding="utf-8")
        match = re.search(r"const diagnosticSourceLink=/(.+)/;\n", app_js)
        pattern = re.compile(match.group(1).replace(r"\/", "/"))
        self.assertTrue(pattern.fullmatch(source.source_url(COMMIT, HANDOFF, 57)))
        for unsafe in ("javascript:alert(1)", "https://evil.example/blob/" + COMMIT + "/app/static/a.js#L1",
                       "https://github.com/o/r/blob/main/app/static/a.js#L1",
                       "https://github.com/o/r/blob/cde219a1e184/app/static/a.js#L1",
                       f"https://github.com/o/r/blob/{COMMIT}/app/static/a.js#L1\" onclick=\"x",
                       f"https://github.com/o/r/blob/{COMMIT}/app/static/a.js?token=abc#L1",
                       f"https://github.com/o/r/blob/{COMMIT}/.env#L1"):
            self.assertIsNone(pattern.fullmatch(unsafe), unsafe)


@unittest.skipUnless(PG_URL.startswith("postgresql+asyncpg://"), "requires disposable monitoring PostgreSQL")
class PostgresPrecisionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = pwa.settings(MONITORING_MODE="all", MONITORING_PUSH_ENABLED=True, admin_id_list=[],
                                     MONITORING_SOURCE_COMMIT=COMMIT)
        self._sessions = pg_sessions(PG_URL, users=())
        self.sessions = await self._sessions.__aenter__()
        self.addAsyncCleanup(self._sessions.__aexit__, None, None, None)
        self.cookies = {}
        for uid in (1, 3):
            async with self.sessions() as db, db.begin():
                learner = pwa.user(uid, 1000 + uid)
                db.add(learner)
                await db.flush()
                self.cookies[uid] = await PwaAuthService(db, self.settings)._mint_session(
                    learner, DesktopLinkRequest(installation_key_hash=uuid4().hex * 2))
        self.app = FastAPI()
        self.app.include_router(create_pwa_auth_router(session_factory=self.sessions, settings_obj=self.settings))
        self.app.include_router(create_monitoring_intake_router(session_factory=self.sessions,
                                                                settings_obj=self.settings))

    async def post(self, *events, owner=1, csrf=None, raw=None):
        async with AsyncClient(transport=ASGITransport(app=self.app), base_url=pwa.ORIGIN,
                               cookies={PWA_SESSION_COOKIE: self.cookies[owner]}) as client:
            if csrf is None:
                csrf = (await client.get("/api/v3/pwa-auth/session")).json()["csrf"]
            body = raw if raw is not None else {"schema": "diag.v1", "events": list(events)}
            return await client.post(INTAKE, json=body, headers={"Origin": pwa.ORIGIN, "X-HSK-PWA-CSRF": csrf})

    async def listing(self, **filters):
        async with admin_client(self.sessions) as admin:
            reply = await admin.post(LIST, json={"source": "diagnostic", **filters})
        self.assertEqual(reply.status_code, 200, reply.text)
        return reply

    async def receipts(self):
        async with self.sessions() as db:
            return (await db.scalars(select(DiagnosticReceipt).order_by(DiagnosticReceipt.id))).all()

    async def test_browser_owner_intake_reaches_the_admin_detail_with_a_verified_link(self):
        current, stale = blob_token(HANDOFF), "0123456789ab"
        guide = hashlib.sha256((ROOT / catalog.DEBUG_ASSETS["li_onboarding_install"]).read_bytes()).hexdigest()[:12]
        event = js_event(error_name="TypeError", reason_code="null_access",
                         location=place(asset_version=current),
                         frames=[place("li_onboarding_install", 120, 14, asset_version=guide),
                                 place("hsk_character_pack", 8, 3, asset_version=stale),
                                 place("voice_live", 44, 2)])
        reply = await self.post(event)
        self.assertEqual((reply.status_code, reply.json()["accepted"]), (200, 1), reply.text)
        retry = await self.post(event)
        self.assertEqual(retry.json()["duplicates"], 1, "an idempotent retry stores nothing new")
        receipt, = await self.receipts()
        self.assertEqual((receipt.user_id, receipt.error_name, receipt.reason_code, receipt.category,
                          receipt.source_commit), (1, "TypeError", "null_access", "type", COMMIT))
        self.assertEqual([(p["asset_id"], p["line"], p["column"], p["verified"]) for p in receipt.locations], [
            (HANDOFF, 57, 9, True), ("li_onboarding_install", 120, 14, True),
            ("hsk_character_pack", 8, 3, False), ("voice_live", 44, 2, False)])
        row, = (await self.listing(platform="iphone_pwa")).json()["items"]
        self.assertEqual((row["feature_code"], row["failure_code"], row["occurrences"], row["affected_accounts"]),
                         ("distribution_handoff", "js_uncaught", 1, 1))
        sample = row["sample"]
        self.assertEqual({key: sample[key] for key in ("category", "error_name", "reason_code", "app_version")},
                         {"category": "type", "error_name": "TypeError", "reason_code": "null_access",
                          "app_version": event["app_version"]})
        self.assertEqual(sample["received_at"], receipt.received_at.isoformat())
        base = f"https://github.com/akbarholturaev11-lang/HSK-AI-Bot/blob/{COMMIT}/"
        self.assertEqual(sample["locations"], [
            {"asset_id": HANDOFF, "path": "app/static/iphone-pwa-handoff.js", "line": 57, "column": 9,
             "source_url": base + "app/static/iphone-pwa-handoff.js#L57"},
            {"asset_id": "li_onboarding_install", "path": "app/static/course_v3_data/li-onboarding-install.js",
             "line": 120, "column": 14,
             "source_url": base + "app/static/course_v3_data/li-onboarding-install.js#L120"},
            # A stale or missing asset version keeps its coordinates, never a link.
            {"asset_id": "hsk_character_pack", "path": "app/static/assets/characters/hsk-character-pack.js",
             "line": 8, "column": 3, "source_url": None},
            {"asset_id": "voice_live", "path": "app/static/voice-live.js", "line": 44, "column": 2,
             "source_url": None},
        ])
        self.assertTrue({"user_id", "telegram_id", "message", "fingerprint", "stack", "event_id",
                         "asset_version", "source_commit"}.isdisjoint(row))
        self.assertTrue({"asset_version", "verified", "user_id", "event_id"}.isdisjoint(sample["locations"][0]))

    async def test_no_link_without_a_deployed_commit_or_with_a_cache_token_as_commit(self):
        for value in ("", "20261114-cde219a1e184", blob_token(HANDOFF)):
            self.settings.MONITORING_SOURCE_COMMIT = value
            reply = await self.post(js_event(error_name="TypeError", location=place(asset_version=blob_token(HANDOFF))))
            self.assertEqual(reply.json()["accepted"], 1, reply.text)
        for receipt in await self.receipts():
            self.assertIsNone(receipt.source_commit)
            self.assertTrue(receipt.locations[0]["verified"])
        sample = (await self.listing()).json()["items"][0]["sample"]
        self.assertEqual([(p["path"], p["line"], p["source_url"]) for p in sample["locations"]],
                         [("app/static/iphone-pwa-handoff.js", 57, None)])

    async def test_hostile_requests_store_nothing_private_anywhere(self):
        hostile = [
            {"schema": "diag.v1", "events": [js_event(message="Cannot read properties of undefined (reading 'secretProp')")]},
            {"schema": "diag.v1", "events": [js_event(stack="evilFn@https://hsk.test/a.js?token=abc:1:1")]},
            {"schema": "diag.v1", "events": [js_event(location=place(url="https://hsk.test/a.js?token=abc"))]},
            {"schema": "diag.v1", "events": [js_event(location=place(), frames=[place(function="evilFn")])]},
            {"schema": "diag.v1", "events": [js_event(location=place(), frames=[place()] * 4000)]},
        ]
        logger = logging.getLogger()
        with self.assertLogs(logger, level="DEBUG") as logs:
            logger.debug("capture marker")
            for body in hostile[:4]:
                reply = await self.post(raw=body)
                self.assertEqual((reply.status_code, reply.json()["error"]), (422, "forbidden_field"), reply.text)
            oversized = await self.post(raw=hostile[4])
            self.assertEqual(oversized.status_code, 413, oversized.text)
            mixed = await self.post(
                js_event(error_name="TypeError", location=place("../../etc/passwd")),
                js_event(error_name="<script>alert(1)</script>"),
                js_event(error_name="TypeError", reason_code="secretProp"),
                js_event(location=place("learner@example.com")),
                js_event(location=place(), frames=[place(line=n + 1) for n in range(6)]),
                js_event(location=place(asset_version="token=abc")),
                js_event(error_name="TypeError", reason_code="null_access", location=place()),
            )
            self.assertEqual((mixed.json()["accepted"], mixed.json()["rejected"]), (1, 6), mixed.text)
            forged = await self.post(js_event(error_name="TypeError", location=place()), csrf="forged-csrf")
            self.assertIn(forged.status_code, (401, 403), forged.text)
            listing = await self.listing()
        async with self.sessions() as db:
            stored = [json.dumps([dict(row._mapping) for row in (await db.execute(text(f"SELECT * FROM {table}"))).all()],
                                 default=str)
                      for table in ("diagnostic_receipts", "diagnostic_incidents", "admin_pwa_push_outbox",
                                    "admin_pwa_inbox_triage", "admin_pwa_inbox_triage_audit")]
            self.assertEqual(await db.scalar(select(func.count()).select_from(DiagnosticReceipt)), 1)
        surfaces = stored + [listing.text, "\n".join(logs.output)]
        for secret in SECRETS:
            for surface in surfaces:
                self.assertNotIn(secret, surface, secret)

    async def test_last_sample_is_one_receipt_and_prefers_the_latest_with_a_location(self):
        now = datetime.now(timezone.utc)

        async def record(minutes, owner=1, **debug):
            version = debug.pop("version", "20261114-abcdef123456")
            events, rejected = parse(js_event(app_version=version, build=int(version[:8]), **debug))
            self.assertFalse(rejected)
            async with self.sessions() as db, db.begin():
                result = await ingest(db, owner_user_id=owner, events=events, now=now - timedelta(minutes=minutes),
                                      settings_obj=self.settings)
                return result.touched[0][0].id

        same = dict(error_name="TypeError", reason_code="null_access")
        incident = await record(60 * 24 * (catalog.RECEIPT_RETENTION_DAYS + 1), **same,
                                location=place(line=1))  # outside retention: never a sample
        await record(50, **same, location=place(line=10), version="20261101-abcdef123456")
        await record(40, owner=3, **same, location=place(line=20), frames=[place(line=21)],
                     version="20261110-abcdef123456")
        await record(30, **same, location=place(line=30), version="20261112-abcdef123456")
        self.assertEqual(await record(20, **same, location=place(line=40)), incident,
                         "one exception identity groups across lines and versions")
        async with self.sessions() as db, db.begin():
            # The two newest receipts keep only their category, as pre-precision ones do.
            await db.execute(text("UPDATE diagnostic_receipts SET locations = NULL WHERE received_at > :cut"),
                             {"cut": now - timedelta(minutes=35)})
        row, = (await self.listing()).json()["items"]
        self.assertEqual((row["occurrences"], row["affected_accounts"], row["last_version"]),
                         (5, 2, "20261114-abcdef123456"))
        sample = row["sample"]
        # The newest receipt with a location: its own time, version, name and reason.
        self.assertEqual((sample["app_version"], sample["error_name"], sample["reason_code"], sample["category"]),
                         ("20261110-abcdef123456", "TypeError", "null_access", "type"))
        self.assertEqual(sample["received_at"], (now - timedelta(minutes=40)).isoformat())
        self.assertEqual([p["line"] for p in sample["locations"]], [20, 21])

        async with self.sessions() as db, db.begin():
            await db.execute(text("UPDATE diagnostic_receipts SET locations = NULL"))
        sample = (await self.listing()).json()["items"][0]["sample"]
        # No location anywhere: the newest receipt with a category, nothing invented.
        self.assertEqual((sample["received_at"], sample["category"], sample["error_name"], sample["locations"]),
                         ((now - timedelta(minutes=20)).isoformat(), "type", "TypeError", []))
        async with self.sessions() as db, db.begin():
            await db.execute(text("UPDATE diagnostic_receipts SET category = NULL"))
        row, = (await self.listing()).json()["items"]
        self.assertIsNone(row["sample"])
        self.assertEqual(row["occurrences"], 5)

    async def test_pre_precision_receipts_show_the_category_and_no_fabricated_location(self):
        reply = await self.post(js_event())
        self.assertEqual(reply.json()["accepted"], 1, reply.text)
        sample = (await self.listing()).json()["items"][0]["sample"]
        self.assertEqual({key: sample[key] for key in ("category", "error_name", "reason_code", "locations")},
                         {"category": "type", "error_name": None, "reason_code": None, "locations": []})
        handled = client_event("lessons", "load_failed", "lesson_open", "iphone_pwa")
        self.assertEqual((await self.post(handled)).json()["accepted"], 1)
        rows = {row["failure_code"]: row for row in (await self.listing()).json()["items"]}
        self.assertIsNone(rows["load_failed"]["sample"])

    async def test_distinct_js_errors_on_one_page_are_separate_incidents(self):
        """NXT-011 acceptance: split by identity, dedupe repeats, explicit page-level group."""
        null_access = dict(error_name="TypeError", reason_code="null_access")
        first = js_event(**null_access, location=place(line=10))
        reply = await self.post(first, js_event(error_name="ReferenceError", category="reference",
                                                reason_code="not_defined", location=place(line=80)))
        self.assertEqual(reply.json()["accepted"], 2, reply.text)
        # A retry is idempotent; the same error again (another line, version, account) counts once more.
        self.assertEqual((await self.post(first)).json()["duplicates"], 1)
        again = js_event(**null_access, location=place(line=12), app_version="20261121-abcdef123456",
                         build=20261121)
        self.assertEqual((await self.post(again, owner=3)).json()["accepted"], 1)
        self.assertEqual((await self.post(js_event())).json()["accepted"], 1)
        rows = (await self.listing()).json()["items"]
        by_name = {(row["grouping"], (row["sample"] or {}).get("error_name")): row for row in rows}
        self.assertEqual(set(by_name), {("exception", "TypeError"), ("exception", "ReferenceError"), ("page", None)})
        self.assertEqual((by_name[("exception", "TypeError")]["occurrences"],
                          by_name[("exception", "TypeError")]["affected_accounts"]), (2, 2))
        self.assertEqual(by_name[("exception", "ReferenceError")]["occurrences"], 1)
        self.assertEqual(by_name[("page", None)]["occurrences"], 1)
        async with self.sessions() as db:
            stored = (await db.scalars(select(DiagnosticIncident.fingerprint))).all()
        self.assertIn(fingerprint("iphone_pwa", "distribution_handoff", "js_uncaught", "pwa_handoff"), stored,
                      "failures without evidence keep the existing page-level incident")
        handled = client_event("lessons", "load_failed", "lesson_open", "iphone_pwa")
        self.assertEqual((await self.post(handled)).json()["accepted"], 1)
        rows = {row["failure_code"]: row for row in (await self.listing()).json()["items"]}
        self.assertIsNone(rows["load_failed"]["grouping"], "only web JS failures carry a grouping")

    async def test_fixed_reopen_alert_and_push_payload_are_unchanged_by_debug_evidence(self):
        from app.db.models.admin_pwa_push import AdminPwaPushSubscription
        from app.db.models.user import User
        from app.services import admin_pwa_push_dispatch as dispatch

        self.settings.ADMIN_PWA_ENABLED = self.settings.ADMIN_PWA_PUSH_ENABLED = True
        self.settings.admin_id_list = [2002]
        seen = datetime.now(timezone.utc)
        async with self.sessions() as db, db.begin():
            db.add(User(id=2, telegram_id=2002, status="free"))
            await db.flush()
            db.add(AdminPwaPushSubscription(
                id=str(uuid4()), user_id=2, endpoint_hash=hashlib.sha256(b"device").hexdigest(),
                encrypted_payload="synthetic-never-sent", platform="iphone", created_at=seen, updated_at=seen))
        debug = dict(error_name="TypeError", reason_code="null_access", location=place(asset_version=blob_token(HANDOFF)))

        def crash():
            return client_event("checkout_payments", "js_uncaught", "checkout", "iphone_pwa", category="type", **debug)

        async def outbox():
            async with self.sessions() as db:
                return (await db.scalars(select(AdminPwaPushOutbox).order_by(AdminPwaPushOutbox.created_at))).all()

        self.assertEqual((await self.post(crash())).json()["accepted"], 1)
        async with self.sessions() as db:
            incident = (await db.scalars(select(DiagnosticIncident))).one()
        self.assertEqual(incident.severity, "critical")  # the catalog's decision, not client metadata
        self.assertEqual([row.diagnostic_kind for row in await outbox()], ["new"])
        async with admin_client(self.sessions) as admin:
            for revision, operation in ((0, "mark_read"), (1, "resolve")):
                reply = await admin.post(TRIAGE, json={"source": "diagnostic", "source_id": incident.id,
                                                       "expected_revision": revision, "operation": operation})
                self.assertEqual(reply.status_code, 200, reply.text)
            self.assertEqual((await self.post(crash())).json()["accepted"], 1)
            row, = (await admin.post(LIST, json={"source": "diagnostic"})).json()["items"]
        self.assertEqual((row["triage_status"], row["occurrences"]), ("read", 2))
        self.assertIsNotNone(row["reopened_at"])
        self.assertEqual(row["sample"]["locations"][0]["line"], 57)
        self.assertEqual([entry.diagnostic_kind for entry in await outbox()], ["new", "reopened"])
        sent = []

        async def capture(subscription, public_data, *args, **kwargs):
            sent.append(json.loads(public_data))

        with patch("app.services.webpush_transport.send_webpush", new=capture):
            for kind in ("new", "reopened"):
                await dispatch._webpush({}, "key", "mailto:qa@example.test", source="diagnostic", kind=kind)
        self.assertEqual(sent, [{"kind": "important", "source": "diagnostic"},
                                {"kind": "reopened", "source": "diagnostic"}])

    async def test_account_deletion_and_retention_remove_debug_evidence(self):
        now = datetime.now(timezone.utc)
        debug = dict(error_name="TypeError", location=place())
        self.assertEqual((await self.post(js_event(**debug), owner=1)).json()["accepted"], 1)
        self.assertEqual((await self.post(js_event(**debug), owner=3)).json()["accepted"], 1)
        async with self.sessions() as db:
            self.assertTrue(await UserRepository(db).delete_by_user_id(1))
            await db.commit()
        self.assertEqual([receipt.user_id for receipt in await self.receipts()], [3])
        row, = (await self.listing()).json()["items"]
        self.assertEqual((row["affected_accounts"], row["occurrences"]), (1, 2))
        self.assertEqual(row["sample"]["locations"][0]["line"], 57)
        async with self.sessions() as db, db.begin():
            await db.execute(text("UPDATE diagnostic_receipts SET received_at = :old"),
                             {"old": now - timedelta(days=catalog.RECEIPT_RETENTION_DAYS + 1)})
        async with self.sessions() as db, db.begin():
            self.assertEqual((await purge_diagnostics(db, now=now))[0], 1)
        self.assertEqual(await self.receipts(), [])
        self.assertIsNone((await self.listing()).json()["items"][0]["sample"])

    async def test_sample_read_uses_the_partial_indexes_not_the_receipt_history(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as db, db.begin():
            event, = parse(js_event(error_name="TypeError", location=place()))[0]
            incident = (await ingest(db, owner_user_id=1, events=[event], now=now - timedelta(days=2),
                                     settings_obj=self.settings)).touched[0][0].id
            # 40,000 newer handled failures on the same incident, none of them a sample.
            await db.execute(text("""
                INSERT INTO diagnostic_receipts (incident_id, user_id, event_id, received_at,
                    client_time_untrusted, outcome, occurrences)
                SELECT :incident, 1, gen_random_uuid()::text, CAST(:now AS timestamptz) - make_interval(secs => n),
                       false, 'failed', 1
                FROM generate_series(1, 40000) AS n"""), {"incident": incident, "now": now})
            await db.execute(text("ANALYZE diagnostic_receipts"))
        sample = (await self.listing()).json()["items"][0]["sample"]
        self.assertEqual(sample["locations"][0]["line"], 57)
        async with self.sessions() as db:
            for column, index in (("locations", "ix_diagnostic_receipts_sample_location"),
                                  ("category", "ix_diagnostic_receipts_sample_category")):
                plan = "\n".join((await db.scalars(text(f"""
                    EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM diagnostic_receipts
                    WHERE incident_id = :incident AND received_at >= :cutoff AND received_at <= :now
                      AND {column} IS NOT NULL
                    ORDER BY received_at DESC, id DESC LIMIT 1"""),
                    {"incident": incident, "cutoff": now - timedelta(days=30), "now": now})).all())
                self.assertIn(index, plan)
                self.assertNotIn("Seq Scan", plan)
                rows = [int(value) for value in re.findall(r"actual time=[^ ]+ rows=(\d+)", plan)]
                self.assertLessEqual(max(rows), 1, plan)

    async def test_migration_0157_upgrade_downgrade_and_guard(self):
        spec = importlib.util.spec_from_file_location("diagnostic_migration_0157", MIGRATION)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        self.assertEqual(migration.down_revision, "0156_diagnostic_monitoring")
        self.assertEqual((await self.post(js_event())).json()["accepted"], 1)

        def columns(connection):
            return {column["name"] for column in inspect(connection).get_columns("diagnostic_receipts")}

        def indexes(connection):
            return {index["name"] for index in inspect(connection).get_indexes("diagnostic_receipts")}

        def exercise(connection):
            ops = Operations(MigrationContext.configure(connection, opts={"target_metadata": Base.metadata}))
            new = {"error_name", "reason_code", "locations", "source_commit"}
            sample = {"ix_diagnostic_receipts_sample_location", "ix_diagnostic_receipts_sample_category"}
            with patch.object(migration, "op", ops):
                migration.downgrade()  # the ORM fixture is at 0157; a pre-precision receipt survives
                self.assertTrue(new.isdisjoint(columns(connection)))
                self.assertTrue(sample.isdisjoint(indexes(connection)))
                self.assertEqual(connection.execute(text("SELECT category FROM diagnostic_receipts")).scalar_one(), "type")
                migration.upgrade()
                self.assertLessEqual(new, columns(connection))
                self.assertLessEqual(sample, indexes(connection))
                definitions = dict(connection.execute(text(
                    "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'diagnostic_receipts' "
                    "AND schemaname = current_schema()")).all())
                self.assertIn("WHERE (locations IS NOT NULL)", definitions["ix_diagnostic_receipts_sample_location"])
                self.assertIn("WHERE (category IS NOT NULL)", definitions["ix_diagnostic_receipts_sample_category"])
                self.assertEqual(connection.execute(text(
                    "SELECT error_name, reason_code, locations::text, source_commit FROM diagnostic_receipts"
                )).one(), (None, None, None, None))
                for column, value in (("error_name", "'TypeError'"), ("reason_code", "'null_access'"),
                                      ("locations", "'[]'::json"), ("source_commit", f"'{COMMIT}'")):
                    with connection.begin_nested() as held:
                        connection.execute(text(f"UPDATE diagnostic_receipts SET {column} = {value}"))
                        with self.assertRaisesRegex(RuntimeError, "Archive diagnostic debug evidence"):
                            migration.downgrade()
                        held.rollback()
                migration.downgrade()
                migration.upgrade()

        async with self.sessions() as db, db.begin():
            await (await db.connection()).run_sync(exercise)


if __name__ == "__main__":
    unittest.main()
