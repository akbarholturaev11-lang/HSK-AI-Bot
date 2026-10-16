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
        self.assertEqual(scripts.get_heads(), ['0104_native_ai_voice_ownership'])
        self.assertIn('0103_native_account_foundation', [r.revision for r in scripts.walk_revisions()])

    def test_legacy_upgrade_backfills_owners_and_preserves_real_telegram_ids(self):
        foundation = migration('0103')
        engine = sa.create_engine('sqlite:///:memory:')
        with engine.begin() as connection:
            connection.execute(sa.text('CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id BIGINT UNIQUE NOT NULL)'))
            connection.execute(sa.text('CREATE TABLE desktop_devices (id TEXT PRIMARY KEY, telegram_id BIGINT NOT NULL)'))
            connection.execute(sa.text('CREATE TABLE desktop_link_requests (id TEXT PRIMARY KEY)'))
            connection.execute(sa.text('INSERT INTO users VALUES (1, 1001)'))
            for table, column in foundation.TABLES.items():
                connection.execute(sa.text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, user_id INTEGER, {column} BIGINT NOT NULL, event_name TEXT, key TEXT, dedupe_key TEXT)'))
                connection.execute(sa.text(f'INSERT INTO {table} (id, {column}, event_name, key, dedupe_key) VALUES (1, 1001, \'opened\', \'notice\', \'one\')'))
            with Operations.context(MigrationContext.configure(connection)):
                migration('0102').upgrade()
                foundation.upgrade()
                foundation.upgrade()
            self.assertTrue({c['name']: c for c in sa.inspect(connection).get_columns('users')}['telegram_id']['nullable'])
            for table, column in foundation.TABLES.items():
                self.assertEqual(connection.execute(sa.text(f'SELECT user_id, {column} FROM {table}')).one(), (1, 1001))
                self.assertTrue({c['name']: c for c in sa.inspect(connection).get_columns(table)}[column]['nullable'])
                if table in foundation.UNIQUE_KEYS:
                    self.assertIn(foundation.UNIQUE_KEYS[table][0], {c['name'] for c in sa.inspect(connection).get_unique_constraints(table)})
            with Operations.context(MigrationContext.configure(connection)):
                foundation.downgrade()
                migration('0102').downgrade()
            self.assertFalse({c['name']: c for c in sa.inspect(connection).get_columns('users')}['telegram_id']['nullable'])
        engine.dispose()

    def test_bootstrap_schema_is_idempotent_and_provider_data_blocks_downgrade(self):
        engine = sa.create_engine('sqlite:///:memory:')
        with engine.begin() as connection:
            Base.metadata.create_all(connection)
            with Operations.context(MigrationContext.configure(connection)):
                migration('0102').upgrade()
                migration('0103').upgrade()
            connection.execute(Base.metadata.tables["users"].insert().values(id=1, telegram_id=None))
            with Operations.context(MigrationContext.configure(connection)):
                with self.assertRaisesRegex(RuntimeError, 'Provider-only'):
                    migration('0102').downgrade()
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
                migration('0102').upgrade()
            self.assertEqual(connection.execute(sa.text("SELECT status FROM desktop_link_requests WHERE id = 'old-link'")).scalar_one(), 'expired')
            self.assertEqual(connection.execute(sa.text("SELECT status FROM desktop_link_requests WHERE id = 'signin'")).scalar_one(), 'pending')
            connection.execute(sa.text("INSERT INTO desktop_link_requests (id, intent, status, bind_session_id) VALUES ('fresh', 'link', 'pending', 'native-session')"))
            with Operations.context(MigrationContext.configure(connection)):
                migration('0102').upgrade()
            self.assertEqual(connection.execute(sa.text("SELECT status FROM desktop_link_requests WHERE id = 'fresh'")).scalar_one(), 'pending')
        engine.dispose()
