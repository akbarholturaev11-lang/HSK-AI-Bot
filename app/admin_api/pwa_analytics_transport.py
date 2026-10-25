"""Guarded first-party analytics transport; mounted only with completed projections."""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.admin_api.pwa_analytics_cache import AnalyticsRequest, AdminPwaAnalyticsReader
from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session
from app.admin_api.pwa_webauthn_transport import _body, _guard_post

logger=logging.getLogger(__name__)


def create_admin_pwa_analytics_router(*,settings_obj,session_factory,analytics_reader=None):
    reader=analytics_reader if analytics_reader is not None else AdminPwaAnalyticsReader(
        settings_obj=settings_obj,session_factory=session_factory)
    router=APIRouter(tags=['admin-pwa-analytics'])

    @router.post('/api/admin/v1/analytics')
    async def analytics(request:Request):
        failure=_guard_post(request,settings_obj)
        if failure is not None:return failure
        if request.query_params:return _reply(400,'admin_pwa_invalid_payload')
        cookie=request.cookies.get(ADMIN_PWA_COOKIE_NAME,'')
        if not cookie:return _reply(401,'admin_pwa_unauthorized')
        try:
            query=AnalyticsRequest.model_validate(await _body(request,2048))
        except ValidationError:
            return _reply(400,'admin_pwa_invalid_payload')
        try:
            async with session_factory() as db:
                async with read_transaction(db):
                    actor=await authenticate_admin_pwa_session(db,cookie,settings_obj)
                    if actor is None or actor.auth_method!='webauthn':
                        return _reply(401,'admin_pwa_unauthorized')
            # No auth SQL connection spans the Redis/R2 boundary or refresh wait.
            result=await reader(query)
            failure=_guard_post(request,settings_obj)
            if failure is not None:return failure
            async with session_factory() as db:
                async with read_transaction(db):
                    current=await authenticate_admin_pwa_session(db,cookie,settings_obj)
                    if current is None or current.user_id!=actor.user_id or current.auth_method!='webauthn':
                        return _reply(401,'admin_pwa_unauthorized')
            return JSONResponse({'ok':True,**result},headers=_PRIVATE_HEADERS)
        except Exception:
            logger.error('Admin PWA analytics read unavailable')
            return _reply(503,'admin_pwa_read_unavailable')
    return router
