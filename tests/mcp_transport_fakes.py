"""Explicit admission doubles for HTTP tests that inject no database services.

Persistent admission/audit have independent real DB tests. Never used by app.
"""
async def admit(db, **kwargs):
    return True, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", 60


async def finish(db, **kwargs):
    pass


async def statistics_admit(db, **kwargs):
    return True, 60
