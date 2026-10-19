"""Bounded opt-in deadlines for staging PostgreSQL reached over a remote proxy."""
import os


def postgres_timeout(default: float) -> float:
    raw = os.environ.get("NATIVE_ACCOUNT_TEST_TIMEOUT_SECONDS")
    if raw is None:
        return float(default)
    value = float(raw)
    if not 1 <= value <= 300:
        raise ValueError("Native PostgreSQL test deadline must be between 1 and 300 seconds")
    return max(float(default), value)
