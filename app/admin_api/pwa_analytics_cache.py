"""Lazy first-party section composition of the existing private daily reader."""
import asyncio
from functools import partial
from typing import Literal

from app.admin_api.pwa_analytics import home_overview_metrics
from app.admin_api.pwa_read import StatisticsRequest
from app.admin_api.pwa_statistics_cache import AdminPwaStatisticsReader, StatisticsUnavailable

Section = Literal['home','overview','course','platform','funnel','money','sources','report']


class AnalyticsRequest(StatisticsRequest):
    section: Section = 'home'


async def _home(db,query,*,overview=False):
    if query.platform != 'overall':
        # Platform-specific projections are separate builders; never relabel
        # all-account figures as a selected native client.
        raise StatisticsUnavailable('This section requires its platform projection')
    return await home_overview_metrics(db,period=query.period,overview=overview)


class AdminPwaAnalyticsReader:
    """Construct readers only for implemented sections; no eager loading or IO.

    Router integration follows the completed projection set. The fixed internal
    scopes keep section data out of basic statistics/MCP and isolate R2 objects.
    """
    def __init__(self,*,settings_obj,session_factory,projections=None,refresh_mutex=None,reader_options=None):
        projections=projections if projections is not None else {'home':_home,'overview':partial(_home,overview=True)}
        self._mutex=refresh_mutex if refresh_mutex is not None else asyncio.Lock()
        self._readers={section:AdminPwaStatisticsReader(settings_obj=settings_obj,session_factory=session_factory,
            loader=projection,cache_scope='analytics_'+section+'_v1',refresh_mutex=self._mutex,
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
