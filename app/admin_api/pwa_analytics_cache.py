"""Lazy first-party section composition of the existing private daily reader."""
import asyncio
from functools import partial
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from app.admin_api.pwa_analytics_learning import FUNNEL_TRANSPORTS, learning_metrics, funnel_metrics
from app.admin_api.pwa_analytics_course_platform import COURSE_CLIENTS, course_platform_metrics
from app.admin_api.pwa_analytics_finance import (
    PAYMENT_PLATFORM_SOURCES, money_metrics, platform_sources_metrics, sources_metrics,
)
from app.admin_api.pwa_analytics_platforms import platform_metrics
from app.admin_api.pwa_analytics_pwa_pro import pwa_pro_attempt_funnel
from app.admin_api.pwa_analytics_freshness import platform_freshness
from app.admin_api.pwa_analytics_experiments import experiment_metrics
from app.admin_api.pwa_analytics_states import has_legacy_filter, metric_states
from app.db.models.user import User
from app.db.models.payment import Payment
from app.db.models.course_miniapp_event import CourseMiniAppEvent
from app.db.models.ai_usage import AIUsageEvent
from app.db.models.subscription_entry_event import SubscriptionEntryEvent
from typing import Literal

from app.admin_api.pwa_analytics import home_overview_metrics
from app.admin_api.pwa_read import StatisticsRequest
from app.admin_api.pwa_statistics_cache import AdminPwaStatisticsReader, StatisticsUnavailable

Section = Literal['home','overview','course','platform','funnel','money','sources','report','experiments']
_LEGACY_PLATFORM_SECTIONS = ('home', 'overview', 'platform', 'report')


class AnalyticsRequest(StatisticsRequest):
    section: Section = 'home'


async def section_projection(db,query,*,section):
    result = await _legacy_projection(db, query, section=section)
    if section != 'experiments':
        result['metric_states'] = metric_states(section, query.platform, result['metrics'])
    return result


async def _legacy_projection(db,query,*,section):
    now=datetime.now(timezone.utc)
    since=now-timedelta(days={'weekly':7,'monthly':30}[query.period]) if query.period!='all_time' else None
    if query.platform=='overall' and section in ('home','overview'):
        return await home_overview_metrics(db,period=query.period,now=now,overview=section=='overview')
    result={'platform':query.platform,'period':query.period,'since':since.isoformat() if since else None,
        'generated_at':now.isoformat(),'timezone':'Asia/Shanghai','platform_counts_overlap':True,
        'scope':{'section':section},'source':'first-party stored aggregate projections','available':True}
    # A registry entry describes response shape. It cannot authorize an
    # Overall-only SQL loader to return global numbers for a platform.
    scoped = section in _LEGACY_PLATFORM_SECTIONS and has_legacy_filter(section, query.platform)
    scoped = scoped or (section == 'money' and query.platform in PAYMENT_PLATFORM_SOURCES)
    scoped = scoped or (section == 'funnel' and query.platform in FUNNEL_TRANSPORTS)
    scoped = scoped or (section == 'course' and query.platform in COURSE_CLIENTS)
    # R3: entries carry the route-set client column.
    scoped = scoped or (section == 'sources' and query.platform in PAYMENT_PLATFORM_SOURCES)
    if query.platform != 'overall' and not scoped:
        reason = 'not_instrumented' if section in _LEGACY_PLATFORM_SECTIONS else 'attribution_not_audited'
        result.update(available=False, metrics=None, reason=reason)
    elif section in ('platform','home','overview'):
        result['metrics']=await platform_metrics(db,since=since,now=now,platform=query.platform)
        result['scope']['period_filter_applied']=False
    elif section=='course' and query.platform!='overall':
        result['metrics']=await course_platform_metrics(db,platform=query.platform,since=since,now=now)
    elif section=='course':result['metrics']=await learning_metrics(db,period=query.period,since=since,now=now)
    elif section=='funnel':
        result['metrics']=await funnel_metrics(db,since=since,now=now,platform=query.platform)
        if query.platform in ('overall','iphone_pwa'):
            # F8 is PWA-only; it sits beside the unchanged legacy attempt funnel.
            result['metrics']['pwa_pro_attempt_funnel']=await pwa_pro_attempt_funnel(db,since=since,now=now)
    elif section=='money':result['metrics']=await money_metrics(db,since=since,now=now,platform=query.platform)
    elif section=='sources' and query.platform!='overall':
        result['metrics']=await platform_sources_metrics(db,platform=query.platform,since=since,now=now)
    elif section=='sources':result['metrics']=await sources_metrics(db,since=since,now=now)
    elif section=='experiments':result['metrics']=await experiment_metrics(db,since=since,now=now)
    else:
        quality=[]
        for key,model,column in (('accounts',User,User.created_at),('payments',Payment,Payment.submitted_at),
                ('learning',CourseMiniAppEvent,CourseMiniAppEvent.created_at),('ai',AIUsageEvent,AIUsageEvent.created_at),
                ('subscription',SubscriptionEntryEvent,SubscriptionEntryEvent.created_at)):
            count,latest=(await db.execute(select(func.count(),func.max(column)).select_from(model).where(column<=now))).one()
            quality.append({'source':key,'records':count,'latest_at':latest.isoformat() if latest else None})
        result['scope']['quality']='all stored records through generated_at; independent of platform and period'
        result['metrics']={'quality':quality,'daily_cache_hours':24,'detail_row_limit':5000,
            'exact_currencies':True,'ai_is_estimate':True,'platform_counts_overlap':True,
            # D7: per-platform freshness, also independent of the selected filter.
            'platform_freshness':await platform_freshness(db,now=now)}
    return result


class AdminPwaAnalyticsReader:
    """Construct readers only for implemented sections; no eager loading or IO.

    Router integration follows the completed projection set. The fixed internal
    scopes keep section data out of basic statistics/MCP and isolate R2 objects.
    """
    def __init__(self,*,settings_obj,session_factory,projections=None,refresh_mutex=None,reader_options=None):
        projections=projections if projections is not None else {section:partial(section_projection,section=section) for section in ('home','overview','course','platform','funnel','money','sources','report','experiments')}
        self._mutex=refresh_mutex if refresh_mutex is not None else asyncio.Lock()
        self._readers={section:AdminPwaStatisticsReader(settings_obj=settings_obj,session_factory=session_factory,
            loader=projection,cache_scope=f"analytics_{section}_v{1 if section == 'experiments' else 2}",refresh_mutex=self._mutex,
            **(reader_options or {})) for section,projection in projections.items()}

    async def __call__(self,query):
        query=AnalyticsRequest.model_validate(query.model_dump())
        reader=self._readers.get(query.section)
        if reader is None:
            raise StatisticsUnavailable('Analytics section unavailable')
        result=await reader(StatisticsRequest(period=query.period,platform=query.platform))
        if result.get('scope',{}).get('section') != query.section:
            raise StatisticsUnavailable('Analytics section mismatch')
        return result

    async def aclose(self):
        for reader in self._readers.values():
            await reader.aclose()
