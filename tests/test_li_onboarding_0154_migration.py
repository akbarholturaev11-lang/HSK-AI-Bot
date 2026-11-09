"""Rehearse additive Li onboarding migration 0154 on a legacy schema.

This verifies old profile goal/streak preservation and reentrant upgrades.
PostgreSQL CHECK/constraint behavior still needs an isolated Postgres rehearsal.
"""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

REVISION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic/versions/0154_li_onboarding_choices.py"
)


class LiOnboardingMigration0154Tests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.conn = self.engine.connect()
        self.conn.execute(text("""
            CREATE TABLE course_miniapp_profiles (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                goal VARCHAR(64),
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0
            )
        """))
        self.conn.execute(text("""
            INSERT INTO course_miniapp_profiles
                (id, user_id, goal, current_streak, longest_streak)
            VALUES (1, 42, 'study_china', 9, 15)
        """))
        self.conn.commit()
        spec = importlib.util.spec_from_file_location("li_0154_qa", REVISION_PATH)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.ops = Operations(MigrationContext.configure(self.conn))

    def tearDown(self):
        self.conn.close()
        self.engine.dispose()

    def _upgrade(self):
        with patch.object(self.migration, "op", self.ops):
            self.migration.upgrade()

    def test_revision_is_linear_extension_of_inline_pro_head(self):
        self.assertEqual(self.migration.revision, "0154_li_onboarding_choices")
        self.assertEqual(self.migration.down_revision, "0153_pwa_inline_funnel")

    def test_additive_upgrade_preserves_existing_goal_and_streak(self):
        self._upgrade()
        self._upgrade()  # metadata-first QA also starts with columns present
        columns = {
            column["name"]: column
            for column in inspect(self.conn).get_columns("course_miniapp_profiles")
        }
        self.assertIn("goals_json", columns)
        self.assertIn("streak_target_days", columns)
        self.assertTrue(columns["goals_json"]["nullable"])
        self.assertTrue(columns["streak_target_days"]["nullable"])
        row = self.conn.execute(text("""
            SELECT goal, goals_json, streak_target_days,
                   current_streak, longest_streak
            FROM course_miniapp_profiles WHERE user_id=42
        """)).one()
        self.assertEqual(tuple(row), ("study_china", None, None, 9, 15))

    def test_reentrant_upgrade_does_not_overwrite_saved_user_preferences(self):
        self._upgrade()
        self.conn.execute(text("""
            UPDATE course_miniapp_profiles
               SET goals_json='["study_china","travel"]',
                   streak_target_days=14
             WHERE user_id=42
        """))
        self._upgrade()
        row = self.conn.execute(text("""
            SELECT goal, goals_json, streak_target_days,
                   current_streak, longest_streak
            FROM course_miniapp_profiles WHERE user_id=42
        """)).one()
        self.assertEqual(
            tuple(row), ("study_china", '["study_china","travel"]', 14, 9, 15)
        )


if __name__ == "__main__":
    unittest.main()
