#!/bin/bash
set -e

echo "=== Alembic migration check ==="

if ! CURRENT=$(alembic current 2>&1); then
    echo "Alembic current failed. Refusing to continue:"
    echo "$CURRENT"
    exit 1
fi
echo "Alembic current output:"
echo "$CURRENT"

# A clean PostgreSQL cluster does not have course tables in legacy Alembic
# revisions 0001..0011. Attempting upgrade-from-base writes a partial schema,
# then fails at 0011 (course_progress missing). Refuse that unsafe bootstrap.
# Operator must first create a verified 0102 schema-only *QA* copy.
# Production already-versioned schemas continue through normal migrations.
if ! echo "$CURRENT" | grep -qE '^[[:space:]]*([0-9]{4}_[a-zA-Z0-9_]+|[0-9a-f]{4,40})([[:space:]]|$)'; then
    echo "No verified Alembic revision. Refusing unversioned database bootstrap."
    echo "For isolated QA, see docs/UNIVERSAL_NATIVE_ACCOUNT_QA.md."
    exit 1
fi

echo "Versioned database found; running normal Alembic upgrade."
echo "=== Running alembic upgrade head ==="
alembic upgrade head
echo "Migrations OK."

echo "=== Starting uvicorn ==="
export PYTHONUNBUFFERED=1
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
