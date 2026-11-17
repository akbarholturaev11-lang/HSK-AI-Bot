"""Fault injection for the conversion-funnel writer's own DB sessions.

`ConversionFunnelService` opens its own session per write. Patch
`app.services.conversion_funnel_service.async_session_maker` with
`FlakyFunnelSessions(real_sessions, ...)` to make chosen session openings fail.
Calls are counted from 1 in the order the service opens sessions:

- `drop`: the session fails before any statement, like a dropped connection;
- `lost_ack`: the commit is stored, then the caller still gets an exception
  (the database applied it but the acknowledgement was lost).
"""
from contextlib import asynccontextmanager


class FlakyFunnelSessions:
    def __init__(self, sessions, *, drop=(), lost_ack=()):
        self.sessions = sessions
        self.drop = set(drop)
        self.lost_ack = set(lost_ack)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls in self.drop:
            return self._dropped()
        if self.calls in self.lost_ack:
            return self._lost_ack()
        return self.sessions()

    @asynccontextmanager
    async def _dropped(self):
        raise ConnectionResetError("simulated dropped DB connection")
        yield  # pragma: no cover - makes this an async generator

    @asynccontextmanager
    async def _lost_ack(self):
        async with self.sessions() as session:
            commit = session.commit

            async def commit_then_drop():
                await commit()
                raise ConnectionResetError("simulated lost commit acknowledgement")

            session.commit = commit_then_drop
            yield session
