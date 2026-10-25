"""Explicit bounded orphan-triage cleanup; original records/audits are untouched."""
from sqlalchemy import and_, delete, or_, select, tuple_

from app.db.models.admin_pwa_inbox_triage import AdminPwaInboxTriage
from app.db.models.admin_pwa_native_report import AdminPwaNativeReport
from app.db.models.bot_feedback import BotFeedback
from app.db.models.message import Message
from app.db.models.payment import Payment
from app.db.models.release_feedback import ReleaseFeedbackResponse

SOURCE_MODELS={'android':AdminPwaNativeReport,'bot':BotFeedback,'payment':Payment,
               'release':ReleaseFeedbackResponse,'technical':Message}


async def scan_orphaned_inbox_triage(db,*,execute=False,limit=100,after=None):
    """One primary-key page, at most five indexed source-ID existence checks.

    The caller owns the transaction and optional timeout. A dry run has no
    locks/writes. Cleanup locks only this metadata page with SKIP LOCKED, then
    deletes exact missing-source keys. A concurrent source deletion after its
    existence check is intentionally deferred to the next explicit sweep.
    """
    if type(limit) is not int or not 1<=limit<=1000:
        raise ValueError('Limit must be 1..1000')
    if after is not None and (not isinstance(after,tuple) or len(after)!=2 or
            after[0] not in SOURCE_MODELS or type(after[1]) is not int or not 0<after[1]<=2_147_483_647):
        raise ValueError('Invalid triage cursor')
    query=select(AdminPwaInboxTriage.source,AdminPwaInboxTriage.source_id)
    if after is not None:
        query=query.where(or_(AdminPwaInboxTriage.source>after[0],and_(
            AdminPwaInboxTriage.source==after[0],AdminPwaInboxTriage.source_id>after[1])))
    query=query.order_by(AdminPwaInboxTriage.source,AdminPwaInboxTriage.source_id).limit(limit)
    if execute:query=query.with_for_update(skip_locked=True)
    rows=(await db.execute(query)).all();missing=[]
    for source,model in SOURCE_MODELS.items():
        ids=[row.source_id for row in rows if row.source==source]
        if not ids:continue
        existing=set((await db.scalars(select(model.id).where(model.id.in_(ids)))).all())
        missing.extend((source,key) for key in ids if key not in existing)
    if execute and missing:
        await db.execute(delete(AdminPwaInboxTriage).where(tuple_(
            AdminPwaInboxTriage.source,AdminPwaInboxTriage.source_id).in_(missing)))
    # A full page offers a continuation even if the next page is empty. This
    # avoids a COUNT(*) or an extra global lookahead query just for progress.
    cursor=(rows[-1].source,rows[-1].source_id) if len(rows)==limit else None
    return {'scanned':len(rows),'orphan_candidates':len(missing),'removed':len(missing) if execute else 0,
            'next_cursor':cursor,'mode':'purge' if execute else 'dry_run'}
