"""Explicit anonymous reporting, actual read-only databases and scrubbed CLI IO."""
import argparse
import asyncio
import contextlib
from datetime import date, datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import event, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
from app.db.models.user import User
from app.services.smart_reminder_baseline import MEMBER, TOTAL, VERSION, windows
from scripts import smart_reminder_baseline_report as cli
from tests.test_smart_reminder_analysis import PG_URL

ROOT=Path(__file__).resolve().parents[1]


class InputTests(unittest.TestCase):
    def test_exact_month_and_real_calendar_required(self):
        self.assertEqual(cli.month_argument("2026-10"),date(2026,10,1))
        for value in ("2026-1","2026-00","2026-13","0000-01","2026-10-01"," 2026-10","２０２６-10"):
            with self.assertRaises(argparse.ArgumentTypeError): cli.month_argument(value)

    def test_invalid_targets_fail_without_opening_engine(self):
        with TemporaryDirectory() as directory:
            for value in ("", "sqlite+aiosqlite:///:memory:","sqlite+aiosqlite:///relative.db",
                    "sqlite+aiosqlite:////nonexistent/hsk-smart-report.db",
                    "sqlite+aiosqlite:///"+directory,"mysql+aiomysql://qa:private@host/db",
                    "postgresql+asyncpg:///db","postgresql+asyncpg://host/",
                    "postgresql+asyncpg://host:99999/db","postgresql+asyncpg://host/db?ssl=disable",
                    "postgresql+asyncpg://host/db?server_settings=private",
                    "postgresql+asyncpg://host/db?ssl=require&ssl=verify-full"):
                with self.subTest(target_kind=value.split(':')[0]),self.assertRaises(cli.BaselineReportError):
                    cli.validate_target(value)

    def test_sqlite_query_cannot_override_read_only_policy(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/"existing.db";path.touch()
            with self.assertRaises(cli.BaselineReportError): cli.validate_target("sqlite+aiosqlite:///"+str(path)+"?mode=rw")
            target=cli.validate_target("sqlite+aiosqlite:///"+str(path))
            self.assertEqual(dict(target.query),{"mode":"ro","uri":"true"})

    def test_postgres_alias_and_ssl_cannot_override_startup_guards(self):
        for prefix in ("postgres","postgresql","postgresql+asyncpg"):
            target=cli.validate_target(prefix+"://qa:private@db.example/database?ssl=verify-full")
            self.assertEqual(target.drivername,"postgresql+asyncpg")
            engine=SimpleNamespace()
            with patch.object(cli,"create_async_engine",return_value=engine) as create:
                self.assertIs(cli.readonly_engine(target),engine)
            kwargs=create.call_args.kwargs
            self.assertEqual(dict(create.call_args.args[0].query),{})
            self.assertEqual(kwargs["connect_args"]["server_settings"]["default_transaction_read_only"],"on")
            self.assertEqual(kwargs["connect_args"]["ssl"],"verify-full")
            self.assertEqual(kwargs["connect_args"]["timeout"],3)
            self.assertFalse(kwargs["echo"])
            self.assertTrue(kwargs["hide_parameters"])

    def test_missing_target_never_falls_back_to_application_database(self):
        with patch.dict(os.environ,{"DATABASE_URL":"postgresql://private:private@private/private"},clear=True), \
                patch.object(cli,"readonly_engine",side_effect=AssertionError("no explicit target")), \
                contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(cli.main(["--month","2026-10"]),2)
        self.assertEqual(error.getvalue(),"baseline_database_target_required\n")

    def test_raw_connection_failure_never_prints_credentials_or_traceback(self):
        with patch.dict(os.environ,{cli.TARGET_ENV:"private-url"},clear=True), \
                patch.object(cli,"read_report",side_effect=RuntimeError("postgresql://private-token@private-host/db")), \
                contextlib.redirect_stdout(io.StringIO()) as output,contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(cli.main(["--month","2026-10"]),2)
        self.assertEqual(output.getvalue(),"")
        self.assertEqual(error.getvalue(),"baseline_database_unavailable\n")

    def test_accidental_credential_arguments_are_scrubbed(self):
        for args in (["--database-url","postgresql://private-token@private-host/db"],
                ["--month","private-token"],[],["--month","2026-10","--as-of","2027-01-01"]):
            with contextlib.redirect_stderr(io.StringIO()) as error,self.assertRaises(SystemExit) as caught:
                cli.main(args)
            self.assertEqual(caught.exception.code,2)
            self.assertEqual(error.getvalue(),"baseline_arguments_invalid\n")

    def test_real_connection_failure_has_no_url_or_driver_details(self):
        with TemporaryDirectory() as directory:
            env={k:v for k,v in os.environ.items() if k not in {"BOT_TOKEN","DATABASE_URL","REDIS_URL"}}
            env[cli.TARGET_ENV]="postgresql+asyncpg://private-user:private-token@127.0.0.1:1/private-db"
            env["PYTHONPATH"]=str(ROOT)
            result=subprocess.run([sys.executable,"-m","scripts.smart_reminder_baseline_report","--month","2026-10"],
                cwd=directory,env=env,text=True,capture_output=True,timeout=15)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(2,"","baseline_database_unavailable\n"))

    def test_missing_schema_fails_without_creating_or_migrating_tables(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/"empty.db";path.touch()
            env={k:v for k,v in os.environ.items() if k not in {"BOT_TOKEN","DATABASE_URL","REDIS_URL"}}
            env[cli.TARGET_ENV]="sqlite+aiosqlite:///"+str(path);env["PYTHONPATH"]=str(ROOT)
            result=subprocess.run([sys.executable,"-m","scripts.smart_reminder_baseline_report","--month","2026-10"],
                cwd=directory,env=env,text=True,capture_output=True,timeout=15)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(2,"","baseline_database_unavailable\n"))
            self.assertEqual(path.stat().st_size,0)

    def test_dotenv_is_not_loaded_in_an_unconfigured_fresh_process(self):
        with TemporaryDirectory() as directory:
            Path(directory,".env").write_text(cli.TARGET_ENV+"=private-dotenv-token\nDATABASE_URL=private-application-token\n")
            env={k:v for k,v in os.environ.items() if k not in {cli.TARGET_ENV,"DATABASE_URL","BOT_TOKEN","REDIS_URL"}}
            env["PYTHONPATH"]=str(ROOT)
            result=subprocess.run([sys.executable,"-m","scripts.smart_reminder_baseline_report","--month","2026-10"],
                cwd=directory,env=env,text=True,capture_output=True,timeout=15)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(2,"","baseline_database_target_required\n"))


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_date_and_target_never_open_a_connection(self):
        with patch.object(cli,"readonly_engine",side_effect=AssertionError("invalid target SQL")):
            for month in (None,datetime.now(timezone.utc),date(2026,10,2)):
                with self.assertRaises(cli.BaselineReportError): await cli.read_report("private",month)
            with self.assertRaises(cli.BaselineReportError): await cli.read_report("",date(2026,10,1))

    async def test_timeout_cancels_source_and_disposes_dedicated_engine(self):
        from app.services.smart_reminder_baseline import SmartReminderBaselineService
        engine=SimpleNamespace(dispose=AsyncMock());cleaned=asyncio.Event()
        async def hang(*args):
            try: await asyncio.Event().wait()
            finally: cleaned.set()
        with patch.object(cli,"readonly_engine",return_value=engine),patch.object(cli,"async_sessionmaker",return_value=None), \
                patch.object(cli,"REPORT_TIMEOUT",.01),patch.object(SmartReminderBaselineService,"report",side_effect=hang):
            with self.assertRaises(TimeoutError): await cli.read_report("postgresql://localhost/qa",date(2026,10,1))
        self.assertTrue(cleaned.is_set());engine.dispose.assert_awaited_once()

    async def test_parent_cancellation_propagates_after_disposal(self):
        from app.services.smart_reminder_baseline import SmartReminderBaselineService
        engine=SimpleNamespace(dispose=AsyncMock());started=asyncio.Event()
        async def hang(*args): started.set();await asyncio.Event().wait()
        with patch.object(cli,"readonly_engine",return_value=engine),patch.object(cli,"async_sessionmaker",return_value=None), \
                patch.object(SmartReminderBaselineService,"report",side_effect=hang):
            task=asyncio.create_task(cli.read_report("postgresql://localhost/qa",date(2026,10,1)))
            await started.wait();task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
        engine.dispose.assert_awaited_once()

    async def test_source_exception_still_disposes_engine(self):
        from app.services.smart_reminder_baseline import SmartReminderBaselineService
        engine=SimpleNamespace(dispose=AsyncMock())
        with patch.object(cli,"readonly_engine",return_value=engine),patch.object(cli,"async_sessionmaker",return_value=None), \
                patch.object(SmartReminderBaselineService,"report",side_effect=RuntimeError("private-source")):
            with self.assertRaises(RuntimeError): await cli.read_report("postgresql://localhost/qa",date(2026,10,1))
        engine.dispose.assert_awaited_once()


class ReportChecks:
    postgres=False

    async def asyncSetUp(self):
        self.directory=TemporaryDirectory();self.admin=None
        if self.postgres:
            if not PG_URL: self.directory.cleanup();self.skipTest("Owned loopback PostgreSQL required")
            url=make_url(PG_URL)
            if url.host not in {"127.0.0.1","localhost","::1"} or not url.database.startswith("smart_reminder_qa") or url.query:
                raise RuntimeError("Owned loopback QA required")
            self.schema="smart_report_"+uuid4().hex
            self.admin=create_async_engine(url)
            async with self.admin.begin() as c: await c.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            self.url=PG_URL
            self.engine=create_async_engine(url,connect_args={"server_settings":{"search_path":self.schema}})
        else:
            self.path=Path(self.directory.name)/"ҳисобот бўш жой.db"
            self.url="sqlite+aiosqlite:///"+str(self.path)
            self.engine=create_async_engine(self.url)
        async with self.engine.begin() as c: await c.run_sync(Base.metadata.create_all)
        self.now=datetime.now(timezone.utc);self.entry=self.now-timedelta(days=60)
        self.month=self.entry.date().replace(day=1)
        _,end=windows(self.entry,"Etc/UTC")
        async with self.engine.begin() as c:
            await c.execute(insert(User).values(id=1,telegram_id=3001,status="free",full_name="private learner"))
            await c.execute(insert(MEMBER).values(user_id=1,protocol_version=VERSION,source_job_id="private-source-job",
                entered_at=self.entry,timezone_name="Etc/UTC",course_key="hsk1",expires_at=self.entry+timedelta(days=90),
                observed_at=end,observed_active_days=2,observed_units=3,observed_d7=1))
            await c.execute(insert(TOTAL).values(protocol_version=VERSION,cohort_month=self.month,enrolled_accounts=2,
                matures_at=end,observed_accounts=1,observed_active_days=2,observed_units=3,observed_d7_accounts=1))
        self.real_engine=cli.readonly_engine

    async def asyncTearDown(self):
        if hasattr(self,"engine"): await self.engine.dispose()
        if self.admin is not None:
            async with self.admin.begin() as c: await c.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
            await self.admin.dispose()
        self.directory.cleanup()

    def readonly(self,target):
        engine=self.real_engine(target)
        if self.postgres:
            @event.listens_for(engine.sync_engine,"connect")
            def test_schema(connection,_):
                cursor=connection.cursor()
                try: cursor.execute(f'SET search_path TO "{self.schema}"')
                finally: cursor.close()
        return engine

    async def run_report(self,month=None):
        with patch.object(cli,"readonly_engine",side_effect=self.readonly):
            return await cli.read_report(self.url,month or self.month)

    async def snapshot(self):
        async with self.engine.connect() as c:
            return [(await c.execute(select(t))).mappings().all() for t in (MEMBER,TOTAL,User.__table__)]

    async def test_actual_anonymous_projection_preserves_all_sources(self):
        before=await self.snapshot()
        result=await self.run_report()
        self.assertEqual((result["cohort_accounts"],result["observed_accounts"],result["censored_accounts"]),(2,1,1))
        self.assertEqual((result["observed_d7_percent_lower_bound"],result["observed_units_lower_bound"]),(50,3))
        self.assertFalse(result["primary_kpis_available"]);self.assertFalse(result["dispatch_allowed"])
        self.assertIsNone(result["d7_learning_retention"])
        self.assertNotIn("private",json.dumps(result));self.assertNotIn("user_id",json.dumps(result))
        self.assertEqual(before,await self.snapshot())

    async def test_connections_refuse_writes_at_the_database(self):
        engine=self.readonly(cli.validate_target(self.url))
        try:
            async with engine.connect() as c:
                if self.postgres: self.assertEqual(await c.scalar(text("SHOW transaction_read_only")),"on")
                else: self.assertEqual(await c.scalar(text("PRAGMA query_only")),1)
                with self.assertRaises(DBAPIError):
                    await c.execute(text("UPDATE smart_reminder_baseline_totals SET enrolled_accounts=999"))
        finally: await engine.dispose()
        self.assertEqual((await self.run_report())["cohort_accounts"],2)

    async def test_missing_cohort_is_unavailable_not_zero(self):
        result=await self.run_report(self.now.date().replace(day=1))
        self.assertEqual(result["status"],"no_recorded_cohort")
        self.assertIsNone(result["cohort_accounts"]);self.assertIsNone(result["observed_d7_percent_lower_bound"])

    async def test_report_path_never_aggregates_or_reads_learning(self):
        from app.services.smart_reminder_baseline import SmartReminderBaselineService
        with patch.object(SmartReminderBaselineService,"observe_member",side_effect=AssertionError("read-only CLI")), \
                patch("app.services.smart_reminder_baseline.read_account_learning",side_effect=AssertionError("private source")):
            self.assertEqual((await self.run_report())["observed_accounts"],1)




class SQLiteReportTests(ReportChecks,unittest.IsolatedAsyncioTestCase):
    async def test_real_cli_runs_without_bot_or_application_configuration(self):
        env={k:v for k,v in os.environ.items() if k not in {"BOT_TOKEN","DATABASE_URL","REDIS_URL"}}
        env[cli.TARGET_ENV]=self.url;env["PYTHONPATH"]=str(ROOT)
        result=await asyncio.to_thread(subprocess.run,[sys.executable,"-m","scripts.smart_reminder_baseline_report",
            "--month",self.month.strftime("%Y-%m")],cwd=self.directory.name,env=env,text=True,capture_output=True,timeout=15)
        self.assertEqual((result.returncode,result.stderr),(0,""))
        self.assertEqual(json.loads(result.stdout)["observed_d7_percent_lower_bound"],50)
class PostgreSQLReportTests(ReportChecks,unittest.IsolatedAsyncioTestCase): postgres=True
