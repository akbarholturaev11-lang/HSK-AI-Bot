import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text

from app.config import Settings, settings
from app.db.models.ai_usage import AIUsageEvent
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.payment import Payment
from app.db.models.user import User
from app.db.models.voice_practice_session import VoicePracticeSession
from app.services.admin_finance_stats_service import AdminFinanceStatsService
from app.services.admin_miniapp_service import AdminMiniAppService
from app.services.admin_stats_service import approved_revenue_text
from app.services.ai_service import AIUsageResult
from app.services.ai_usage_budget_service import AIUsageBudgetService, PRO_TRIAL_PLAN_TYPE
from scripts.audit_ai_costs import audit
from tests.test_admin_stats_integrity import _StatsDatabaseTestCase


class BillingRegressionTests(_StatsDatabaseTestCase):
    async def test_free_gemini_keeps_tokens_and_budget_but_fallback_is_charged(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            service = AIUsageBudgetService(session)
            budget = await service.create_fixed_budget(
                telegram_id=101, plan_type=PRO_TRIAL_PLAN_TYPE, amount=0, currency="TJS",
                total_budget_usd=0.001, starts_at=now-timedelta(minutes=1),
                ends_at=now+timedelta(days=7),
            )
            with patch.object(settings, "GEMINI_BILLING_TIER", "free"):
                for model in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"):
                    result = await service.record_usage(101, AIUsageResult(
                        content="synthetic", model=model, prompt_tokens=1000,
                        completion_tokens=1000, total_tokens=2000,
                    ), "qa")
                    self.assertEqual(result.cost_usd, 0)
                    self.assertFalse(result.budget_depleted)
                self.assertEqual(service.total_spent_usd(budget), 0)
                self.assertEqual(budget.current_window_spent_usd, 0)
                self.assertTrue((await service.can_use_ai(101)).allowed)
                self.assertIsNone(budget.cooldown_until)
                fallback = await service.record_usage(101, AIUsageResult(
                    content="synthetic", model="o4-mini", prompt_tokens=1000,
                    completion_tokens=1000, total_tokens=2000,
                ), "qa")
                self.assertAlmostEqual(fallback.cost_usd, 0.0055)
                self.assertTrue(fallback.budget_depleted)
                self.assertFalse((await service.can_use_ai(101)).allowed)
            events = (await session.execute(select(AIUsageEvent))).scalars().all()
            self.assertEqual([e.billing_tier for e in events], ["free"]*3+["paid_estimate"])
            self.assertEqual(sum(e.total_tokens for e in events), 8000)

    async def test_paid_setting_and_history_are_not_repriced(self):
        async with self.sessions() as session:
            service = AIUsageBudgetService(session)
            usage = AIUsageResult(content="x", model="gemini-2.5-flash", prompt_tokens=1000,
                                  completion_tokens=1000, total_tokens=2000)
            with patch.object(settings, "GEMINI_BILLING_TIER", "paid"):
                self.assertAlmostEqual((await service.record_usage(101, usage, "qa")).cost_usd, .0028)
            with patch.object(settings, "GEMINI_BILLING_TIER", "free"):
                await service.record_usage(101, usage, "qa")
                session.add(AIUsageEvent(user_telegram_id=101, model=usage.model, source="qa",
                                         total_tokens=2000, cost_usd=.0028))
                await session.flush()
                finance = AdminFinanceStatsService(session)
                self.assertAlmostEqual(await finance._ai_cost_usd(None), .0056)
                rows = await finance._ai_usage_breakdown(None)
                self.assertEqual({r['billing_tier'] for r in rows}, {"free", "paid_estimate", "legacy_estimate"})
                self.assertEqual(sum(r['tokens'] for r in rows), 6000)

    async def test_unknown_model_is_visible_as_unpriced(self):
        async with self.sessions() as session:
            await AIUsageBudgetService(session).record_usage(
                101, AIUsageResult(content="x", model="unknown-model", total_tokens=10), "qa")
            row = (await AdminFinanceStatsService(session)._ai_usage_breakdown(None))[0]
            self.assertEqual(row['billing_tier'], 'unpriced')
            self.assertEqual(row['tokens'], 10)

    async def test_voice_excludes_abandoned_and_empty_completed_sessions(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            for i, status, turns, minutes in [(1, 'abandoned', 0, 420), (2, 'completed', 0, 20),
                                              (3, 'completed', 2, 5)]:
                session.add(VoicePracticeSession(id=str(i), user_telegram_id=101, role='friend',
                    level='hsk1', language='uz', voice='default', status=status, turn_count=turns,
                    started_at=now-timedelta(minutes=minutes), ended_at=now))
            await session.flush()
            result = await AdminMiniAppService(session)._voice_minutes(since=now-timedelta(days=7))
            self.assertEqual(result['sessions'], 1)
            self.assertEqual(result['minutes'], 5)

    async def test_weekly_d7_uses_completed_cohort_and_exact_return_window(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            # cohort = (now-15d, now-8d], not newly registered last week.
            for i, age, return_age in [(1, 9, 1.5), (2, 8, .5), (3, 7, 0), (4, 15, 7.5), (5, 10, 1)]:
                session.add(User(id=i, telegram_id=i, created_at=now-timedelta(days=age)))
                session.add(CourseMiniAppEvent(id=i, telegram_id=i, event_name='miniapp_opened',
                                               created_at=now-timedelta(days=return_age)))
            await session.flush()
            result = await AdminMiniAppService(session)._retention_stats(since=now-timedelta(days=7), now=now)
            self.assertEqual(result['d7']['eligible'], 3)
            self.assertEqual(result['d7']['retained'], 2)
            self.assertEqual(result['d7']['rate'], 66.7)
            self.assertEqual(result['d7']['cohort_end'], (now-timedelta(days=8)).isoformat())

    async def test_approved_revenue_keeps_currencies_and_excludes_pending(self):
        async with self.sessions() as session:
            for i, currency, amount, status in [(1, 'TJS', 100, 'approved'), (2, 'CNY', 50, 'approved'),
                                                (3, 'TJS', 90, 'pending')]:
                session.add(Payment(id=i, user_telegram_id=101, plan_type='1_month',
                                     currency=currency, amount=amount, payment_status=status))
            await session.flush()
            revenue = await approved_revenue_text(session)
            self.assertIn('100 TJS', revenue)
            self.assertIn('50 CNY', revenue)
            self.assertNotIn('150', revenue)
            self.assertNotIn('190', revenue)

    async def test_audit_is_read_only_and_does_not_print_user_ids(self):
        now = datetime.now(timezone.utc)
        async with self.sessions() as session:
            session.add(AIUsageEvent(user_telegram_id=999888777, model='gemini-2.5-flash',
                                    source='qa', total_tokens=20, cost_usd=.01))
            await session.commit()
        async with self.engine.connect() as connection:
            result = await audit(connection, now-timedelta(days=1), now+timedelta(days=1))
            self.assertEqual(result['rows'][0]['tier'], 'legacy_estimate')
            self.assertNotIn('999888777', str(result))
            with self.assertRaises(Exception):
                await connection.execute(text('DELETE FROM ai_usage_events'))

    async def test_audit_supports_pre_migration_schema(self):
        now = datetime.now(timezone.utc)
        async with self.engine.begin() as connection:
            await connection.execute(text("ALTER TABLE ai_usage_events DROP COLUMN billing_tier"))
        async with self.engine.connect() as connection:
            result = await audit(connection, now-timedelta(days=1), now+timedelta(days=1))
            self.assertEqual(result['rows'], [])



def test_billing_tier_config_rejects_typo():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(_env_file=None, GEMINI_BILLING_TIER='fre')


def test_billing_migration_preserves_legacy_costs_and_is_bootstrap_safe():
    from sqlalchemy import create_engine
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/0080_ai_usage_billing_tier.py'
    spec = importlib.util.spec_from_file_location('billing_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE ai_usage_events (id INTEGER PRIMARY KEY, cost_usd FLOAT)'))
        connection.execute(text('INSERT INTO ai_usage_events VALUES (1, 2.5)'))
        with patch.object(module, 'op', Operations(MigrationContext.configure(connection))):
            module.upgrade()
            module.upgrade()
            row = connection.execute(text('SELECT cost_usd, billing_tier FROM ai_usage_events')).one()
            assert tuple(row) == (2.5, 'legacy_estimate')
            module.downgrade()
            assert connection.execute(text('SELECT cost_usd FROM ai_usage_events')).scalar_one() == 2.5
    engine.dispose()
