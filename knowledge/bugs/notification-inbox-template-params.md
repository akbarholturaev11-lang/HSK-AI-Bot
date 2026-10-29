# Notification inbox template arguments

- Sabab: motivation callers store `template_service`, but `record` accepted only `template`; DB commits silently discarded all arguments. Read-side assignment of a replacement JSON dict containing `_rendered` also dirtied ORM state and could persist presentation text.
- Fix: retain either existing template discriminator, remove transient underscore fields on write, and return resolved display text separately from tracked rows.
- Risk: old rows without source arguments cannot recover a translated body; preserve their stored sent text. DB custom/default/disabled precedence and canonical owner/dedupe remain authoritative.
- Prevention: `tests/test_smart_reminder_telegram_content.py` exercises actual commit/reload, repeated language switches, unchanged stored params/body, owner isolation, duplicate rows and broken fallback on SQLite and owned PostgreSQL; retain existing pure language tests.

Template reads also introduce an await after policy evaluation: a still-valid lease does not override a quiet/day boundary crossed during rendering. Re-evaluate current policy after those reads before committing in-flight. The content suite simulates this boundary on SQLite/PostgreSQL and verifies zero Bot calls.
