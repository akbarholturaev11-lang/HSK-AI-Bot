"""Upgrade legacy Telegram data without losing native account ownership."""
import importlib.util
from pathlib import Path
import unittest

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
import sqlalchemy as sa

from app.db import models  # register the complete bootstrap schema
from app.db.base import Base


def migration(number):
    path = next((Path(__file__).resolve().parents[1] / 'alembic/versions').glob(f'{number}_*.py'))
    spec = importlib.util.spec_from_file_location(f'native_migration_{number}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeAccountMigrationTests(unittest.TestCase):
    def test_revision_chain_has_one_complete_head(self):
        scripts = ScriptDirectory.from_config(Config('alembic.ini'))
        self.assertEqual(scripts.get_heads(), ['0108_native_audit_ownership'])
        self.assertLessEqual(len(scripts.get_heads()[0]), 32)
        self.assertEqual([r.revision for r in scripts.iterate_revisions(
            '0108_native_audit_ownership', '0101_account_deletion_requests')], [
                '0108_native_audit_ownership',
                '0107_canonical_referral_owners', '0106_canonical_payment_ownership', '0105_native_ai_voice_ownership', '0104_native_account_foundation',
                '0103_native_identity_accounts', '0102_payment_review_preview'])

    def test_legacy_upgrade_backfills_owners_and_preserves_real_telegram_ids(self):
        foundation = migration('0104')
        ownership = migration('0105')
        engine = sa.create_engine('sqlite:///:memory:')
        with engine.begin() as connection:
            connection.execute(sa.text('CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id BIGINT UNIQUE NOT NULL, payment_preview_available BOOLEAN NOT NULL DEFAULT TRUE, payment_preview_payment_id INTEGER)'))
            connection.execute(sa.text('CREATE TABLE desktop_devices (id TEXT PRIMARY KEY, telegram_id BIGINT NOT NULL)'))
            connection.execute(sa.text('CREATE TABLE desktop_link_requests (id TEXT PRIMARY KEY)'))
            connection.execute(sa.text('INSERT INTO users VALUES (1, 1001, FALSE, 73), (2, 1002, TRUE, NULL)'))
            for table, column in foundation.TABLES.items():
                connection.execute(sa.text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, user_id INTEGER, {column} BIGINT NOT NULL, event_name TEXT, key TEXT, dedupe_key TEXT)'))
                connection.execute(sa.text(f'INSERT INTO {table} (id, {column}, event_name, key, dedupe_key) VALUES (1, 1001, \'opened\', \'notice\', \'one\')'))
            for table in ownership.TABLES:
                connection.execute(sa.text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, user_telegram_id BIGINT NOT NULL)'))
                connection.execute(sa.text(f'INSERT INTO {table} VALUES (1, 1001)'))
            preview_before = connection.execute(sa.text('SELECT id, payment_preview_available, payment_preview_payment_id FROM users ORDER BY id')).all()
            with Operations.context(MigrationContext.configure(connection)):
                migration('0103').upgrade()
                foundation.upgrade()
                ownership.upgrade()
                foundation.upgrade()
                ownership.upgrade()
            self.assertTrue({c['name']: c for c in sa.inspect(connection).get_columns('users')}['telegram_id']['nullable'])
            for table, column in foundation.TABLES.items():
                self.assertEqual(connection.execute(sa.text(f'SELECT user_id, {column} FROM {table}')).one(), (1, 1001))
                self.assertTrue({c['name']: c for c in sa.inspect(connection).get_columns(table)}[column]['nullable'])
                if table in foundation.UNIQUE_KEYS:
                    self.assertIn(foundation.UNIQUE_KEYS[table][0], {c['name'] for c in sa.inspect(connection).get_unique_constraints(table)})
            for table in ownership.TABLES:
                self.assertEqual(connection.execute(sa.text(f'SELECT user_id, user_telegram_id FROM {table}')).one(), (1, 1001))
            self.assertEqual(connection.execute(sa.text('SELECT id, payment_preview_available, payment_preview_payment_id FROM users ORDER BY id')).all(), preview_before)
            with Operations.context(MigrationContext.configure(connection)):
                ownership.downgrade()
                foundation.downgrade()
                migration('0103').downgrade()
            self.assertFalse({c['name']: c for c in sa.inspect(connection).get_columns('users')}['telegram_id']['nullable'])
            self.assertEqual(connection.execute(sa.text('SELECT id, payment_preview_available, payment_preview_payment_id FROM users ORDER BY id')).all(), preview_before)
            preview_column = {c['name']: c for c in sa.inspect(connection).get_columns('users')}['payment_preview_available']
            self.assertFalse(preview_column['nullable'])
            self.assertEqual(preview_column['default'], 'TRUE')
        engine.dispose()

    def test_bootstrap_schema_is_idempotent_and_provider_data_blocks_downgrade(self):
        engine = sa.create_engine('sqlite:///:memory:')
        with engine.begin() as connection:
            Base.metadata.create_all(connection)
            with Operations.context(MigrationContext.configure(connection)):
                migration('0103').upgrade()
                migration('0104').upgrade()
            connection.execute(Base.metadata.tables["users"].insert().values(id=1, telegram_id=None))
            with Operations.context(MigrationContext.configure(connection)):
                with self.assertRaisesRegex(RuntimeError, 'Provider-only'):
                    migration('0103').downgrade()
            self.assertTrue({c['name']: c for c in sa.inspect(connection).get_columns('users')}['telegram_id']['nullable'])
        engine.dispose()

    def test_old_link_proof_expires_without_expiring_new_bound_proofs_on_rerun(self):
        engine = sa.create_engine('sqlite:///:memory:')
        with engine.begin() as connection:
            connection.execute(sa.text('CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id BIGINT NOT NULL)'))
            connection.execute(sa.text('CREATE TABLE desktop_devices (id TEXT PRIMARY KEY, telegram_id BIGINT NOT NULL)'))
            connection.execute(sa.text('CREATE TABLE desktop_link_requests (id TEXT PRIMARY KEY, intent TEXT, status TEXT)'))
            connection.execute(sa.text("INSERT INTO desktop_link_requests VALUES ('old-link', 'link', 'pending'), ('signin', 'signin', 'pending')"))
            with Operations.context(MigrationContext.configure(connection)):
                migration('0103').upgrade()
            self.assertEqual(connection.execute(sa.text("SELECT status FROM desktop_link_requests WHERE id = 'old-link'")).scalar_one(), 'expired')
            self.assertEqual(connection.execute(sa.text("SELECT status FROM desktop_link_requests WHERE id = 'signin'")).scalar_one(), 'pending')
            connection.execute(sa.text("INSERT INTO desktop_link_requests (id, intent, status, bind_session_id) VALUES ('fresh', 'link', 'pending', 'native-session')"))
            with Operations.context(MigrationContext.configure(connection)):
                migration('0103').upgrade()
            self.assertEqual(connection.execute(sa.text("SELECT status FROM desktop_link_requests WHERE id = 'fresh'")).scalar_one(), 'pending')
        engine.dispose()
