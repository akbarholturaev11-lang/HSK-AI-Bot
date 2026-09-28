"""The new device rule must preserve referrals earned before rollout."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


def test_existing_active_referrals_keep_their_discount_progress(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    path = Path(__file__).resolve().parents[1] / "alembic/versions/0090_referral_discount_device.py"
    spec = importlib.util.spec_from_file_location("referral_discount_migration", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE referrals (id INTEGER PRIMARY KEY, status VARCHAR(16), "
            "activated_at DATETIME)"
        ))
        connection.execute(text(
            "INSERT INTO referrals (id, status, activated_at) VALUES "
            "(1, 'active', '2026-09-01 12:00:00'), (2, 'pending', NULL)"
        ))
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        rows = connection.execute(text(
            "SELECT discount_platform, discount_qualified_at FROM referrals ORDER BY id"
        )).all()
    engine.dispose()
    assert rows[0][0] == "legacy"
    assert str(rows[0][1]).startswith("2026-09-01 12:00:00")
    assert rows[1] == ("legacy", None)
