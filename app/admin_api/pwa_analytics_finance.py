"""Aggregate-only finance and source lineage; no raw payment history export."""
from datetime import timedelta

from sqlalchemy import Float, String, and_, case, cast, func, literal, or_, select

from app.admin_api.pwa_analytics import _known
from app.admin_api.pwa_metrics import _window
from app.db.models.ai_usage import AIUsageEvent as Usage
from app.db.models.payment import Payment
from app.db.models.portfolio import PortfolioTransaction as Ledger
from app.db.models.public_site_traffic import PublicSiteTrafficDaily as Traffic, PUBLIC_SITE_TRAFFIC_SOURCES
from app.db.models.subscription_entry_event import SubscriptionEntryEvent as Entry
from app.db.models.user import User
from app.services.admin_miniapp_service import _payment_user_join
from app.services.hsk30_unlock_service import HSK30_UNLOCK_PLAN_TYPE
from app.services.subscription_currency_service import DEFAULT_USD_CNY_RATE, DEFAULT_VISA_LOCAL_RATES
from app.services.subscription_entry_analytics_service import SubscriptionEntryAnalyticsService as Sources

TJS_RATE=float(DEFAULT_VISA_LOCAL_RATES['tjs'])
CNY_RATE=float(DEFAULT_USD_CNY_RATE)
SOURCE_KEYS=tuple(sorted(set(Sources.SOURCE_LABELS)|set(Sources.SOURCE_GROUP_LABELS)|
    {s for values in Sources.SOURCE_GROUP_ALIASES.values() for s in values}))
TIERS=('free','paid_estimate','legacy_estimate','unpriced')


def source_group(column):
    groups=Sources.SOURCE_GROUP_ALIASES
    return case(*[(column.in_(tuple(aliases)),key) for key,aliases in groups.items()],
        (column.like('android_%'),'android_subscription'),(column.like('desktop_%'),'desktop_subscription'),
        (column.in_(tuple(k for k in SOURCE_KEYS if 'limit' in k)),'limits'),
        (column.in_(tuple(k for k in SOURCE_KEYS if 'voice' in k)),'voice'),
        (column.in_(tuple(k for k in SOURCE_KEYS if 'course' in k or k.startswith('v3_'))),'course'),
        else_='unknown')


def currency_key():
    value=func.lower(func.trim(Payment.currency))
    return case((value.in_(('tjs','somoni','сомони')),'TJS'),(value.in_(('usd','$')),'USD'),
        (value.in_(('cny','¥','yuan','юань')),'CNY'),(value=='uzs','UZS'),(value=='rub','RUB'),else_='unknown')


def usd_expression():
    key=currency_key()
    return case((key=='TJS',cast(Payment.amount,Float)/TJS_RATE),(key=='USD',cast(Payment.amount,Float)),
        (key=='CNY',cast(Payment.amount,Float)/CNY_RATE),
        (Payment.base_amount>0,cast(Payment.base_amount,Float)/TJS_RATE),else_=None)


def approved_history(now):
    # Namespaced retained histories cannot collide with canonical account IDs.
    owner=case((User.id.is_not(None),literal('user:')+cast(User.id,String)),
        (Payment.user_telegram_id.is_not(None),literal('legacy:')+cast(Payment.user_telegram_id,String)),
        else_=literal('payment:')+cast(Payment.id,String))
    at=func.coalesce(Payment.reviewed_at,Payment.submitted_at)
    return select(Payment.id.label('id'),User.id.label('account'),owner.label('owner'),
        at.label('at'),Payment.submitted_at.label('submitted'),usd_expression().label('usd'),
        currency_key().label('currency'),Payment.amount.label('amount'),
        func.row_number().over(partition_by=owner,order_by=(at,Payment.id)).label('sequence'))\
        .select_from(Payment).outerjoin(User,_payment_user_join()).where(
            Payment.payment_status=='approved',Payment.plan_type!=HSK30_UNLOCK_PLAN_TYPE,at<=now).subquery()


async def money_metrics(db, *, since, now):
    history=approved_history(now)
    where=_window(history.c.at,since,now)
    count,payers,known_payers,revenue,unpriced,renewals=(await db.execute(select(func.count(),
        func.count(func.distinct(history.c.owner)),func.count(func.distinct(history.c.account)),
        func.coalesce(func.sum(history.c.usd),0),func.count().filter(history.c.usd.is_(None)),
        func.count().filter(history.c.sequence>1)).where(*where))).one()
    currencies=(await db.execute(select(history.c.currency,func.sum(history.c.amount),func.count())
        .where(*where).group_by(history.c.currency))).all()
    ai=(await db.execute(select(func.count(),func.coalesce(func.sum(Usage.cost_usd),0),
        func.coalesce(func.sum(Usage.total_tokens),0)).where(*_window(Usage.created_at,since,now)))).one()
    # Validate model names as product identifiers, never echo arbitrary stored text.
    import re
    tier=_known(Usage.billing_tier,TIERS)
    groups=(await db.execute(select(Usage.model,tier,func.count(),
        func.sum(Usage.total_tokens),func.sum(Usage.cost_usd)).where(*_window(Usage.created_at,since,now))
        .group_by(Usage.model,tier).limit(65))).all()
    breakdown=None if len(groups)>64 else [{'model':model if re.fullmatch(r'(?:gemini|gpt|o[134]|text-embedding|whisper|tts)[a-zA-Z0-9._:-]{0,70}',model or '') else 'unknown',
        'tier':tier,'requests':n,'tokens':int(tokens or 0),'usd':round(float(cost or 0),8)} for model,tier,n,tokens,cost in groups]
    tag=func.lower(func.coalesce(Ledger.source,'')+' '+func.coalesce(Ledger.note,''))
    marketing=and_(Ledger.transaction_type=='expense',or_(*[tag.like(pattern) for pattern in
        ('%marketing%','%reklama%','%реклама%','%ads%','%target%','%таргет%','%cac%','%smm%','%traffic%')]))
    manual,expense,tagged=(await db.execute(select(
        func.coalesce(func.sum(Ledger.amount_usd).filter(and_(Ledger.transaction_type=='profit',Ledger.source=='manual_profit')),0),
        func.coalesce(func.sum(Ledger.amount_usd).filter(Ledger.transaction_type=='expense'),0),
        func.coalesce(func.sum(Ledger.amount_usd).filter(marketing),0))
        .where(*_window(Ledger.created_at,since,now)))).one()
    active_since=since or now-timedelta(days=30)
    active=int(await db.scalar(select(func.count()).select_from(User).where(
        *_window(User.last_active_at,active_since,now))) or 0)
    elapsed=(func.extract('epoch',history.c.at-User.created_at) if db.get_bind().dialect.name=='postgresql'
        else (func.julianday(history.c.at)-func.julianday(User.created_at))*86400)
    first_delay=await db.scalar(select(func.avg(elapsed)).select_from(history).join(User,User.id==history.c.account)
        .where(history.c.sequence==1,history.c.at>=User.created_at,*where))
    new_accounts=int(await db.scalar(select(func.count()).select_from(history).where(history.c.sequence==1,
        history.c.account.is_not(None),*where)) or 0)
    revenue=float(revenue);ai_cost=float(ai[1])
    return {'tagged_marketing_usd':round(float(tagged),4),'new_paying_accounts':new_accounts,
        'tagged_cac_usd':round(float(tagged)/new_accounts,4) if tagged and new_accounts else None,
        'first_payment_seconds':round(float(first_delay)) if first_delay is not None else None,'revenue_usd':round(revenue,4),'unpriced_payments':unpriced,'payments':count,'paying_histories':payers,
        'canonical_payers':known_payers,'renewal_payments':renewals,'first_payments':count-renewals,
        'renewal_percent':round(100*renewals/count,2) if count else None,
        'ai_usd':round(ai_cost,8),'ai_requests':ai[0],'tokens':int(ai[2]),'ai_models':breakdown,
        'manual_profit_usd':round(float(manual),4),'expense_usd':round(float(expense),4),
        'net_usd':round(revenue+float(manual)-float(expense)-ai_cost,4),
        'arpu_usd':round(revenue/active,4) if active else None,'active_denominator':active,
        'arppu_usd':round(revenue/payers,4) if payers else None,'average_payment_usd':round(revenue/count,4) if count else None,
        'currencies':[{'currency':key,'amount':int(amount),'payments':n} for key,amount,n in currencies if key!='unknown'],
        'unknown_currency_payments':sum(n for key,amount,n in currencies if key=='unknown'),
        'usd_basis':{'tjs_per_usd':TJS_RATE,'cny_per_usd':CNY_RATE,'fallback':'stored base_amount TJS',
            'estimate':True,'ai':'stored cost_usd at event write; not provider invoice'},
        'grains':{'payer':'canonical account or separate retained orphan history','renewal':'approved subscription payment after first historical payment; not cohort churn'}}


async def sources_metrics(db, *, since, now):
    # Collapse unknown/custom source text before it crosses the aggregate boundary.
    source=source_group(Entry.source)
    # Canonical entries need their canonical account in the unique key too.
    # The key uses Entry.user_id directly so contradictory transport metadata wins no ownership.
    owner=case((Entry.user_id.is_not(None),literal('user:')+cast(Entry.user_id,String)),
        (User.id.is_not(None),literal('user:')+cast(User.id,String)),
        else_=literal('legacy:')+cast(Entry.telegram_id,String))
    rows=(await db.execute(select(source,func.count(),func.count(func.distinct(owner)))
        .select_from(Entry).outerjoin(User,and_(Entry.user_id.is_(None),Entry.telegram_id>0,User.telegram_id==Entry.telegram_id))
        .where(*_window(Entry.created_at,since,now)).group_by(source))).all()
    # Existing finance definition: nearest entry at/before submission, with no
    # lookback cutoff. It is historical proximity, never a causal conversion rate.
    prior=select(source_group(Entry.source)).where(
        ((Entry.user_id==User.id) | (Entry.user_id.is_(None)&(Entry.telegram_id>0)&(Entry.telegram_id==User.telegram_id))),
        Entry.created_at<=Payment.submitted_at).order_by(Entry.created_at.desc(),Entry.id.desc()).limit(1).correlate(Payment,User).scalar_subquery()
    payment_source=func.coalesce(prior,'unknown')
    at=func.coalesce(Payment.reviewed_at,Payment.submitted_at)
    attribution=(await db.execute(select(payment_source.label('source'),func.count(Payment.id),func.sum(usd_expression()))
        .select_from(Payment).outerjoin(User,_payment_user_join()).where(Payment.payment_status=='approved',
            Payment.plan_type!=HSK30_UNLOCK_PLAN_TYPE,*_window(at,since,now)).group_by(payment_source))).all()
    traffic_start=now.date()-timedelta(days=(now-since).days-1) if since else None
    traffic=(await db.execute(select(Traffic.source,func.sum(Traffic.visits)).where(
        Traffic.visit_day<=now.date(),*([Traffic.visit_day>=traffic_start] if traffic_start else []))
        .group_by(Traffic.source))).all()
    return {'entries':[{'source':s,'visits':n,'histories':unique} for s,n,unique in rows],
        'attribution':[{'source':s,'payments':n,'usd':round(float(usd or 0),4)} for s,n,usd in attribution],
        'traffic':[{'source':s,'visits':int(n)} for s,n in traffic if s in PUBLIC_SITE_TRAFFIC_SOURCES],
        'attribution_basis':'nearest recorded entry at or before payment submission; all prior history; descriptive, not causal',
        'traffic_grain':'anonymous tagged public-site visits by UTC calendar visit_day; not users or registrations',
        'traffic_since':traffic_start.isoformat() if traffic_start else None,'traffic_timezone':'UTC'}
