from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from app.api.desktop_auth import DesktopAuthError, DesktopAuthService
from app.repositories.user_repo import UserRepository
from app.services.ad_placement_service import AD_PLACEMENTS, AUDIENCE_FREE_ONLY, AdPlacementService, normalize_placement
from app.services.entitlements.access_state import has_full_access, resolve_state
from app.services.course_miniapp_analytics_service import CourseMiniAppAnalyticsService

IOS_AD_TYPES=("odiy","hamkorlik","bot")
class IOSAdError(RuntimeError):
    def __init__(self,code:str,status_code:int): super().__init__(code); self.code=code; self.status_code=status_code
class IOSAdViewRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    ad_id:int=Field(ge=1); watched_seconds:int=Field(default=0,ge=0,le=3600)
    lesson_order:int=Field(default=0,ge=0,le=10000); placement:str=Field(default="screen_center",max_length=24)
def create_ios_ads_router(*,session_factory,settings_obj):
    router=APIRouter(tags=["ios-ads"])
    def token(request:Request):
        value=str(request.headers.get("Authorization","") or ""); scheme,sep,t=value.partition(" ")
        return t.strip() if sep and scheme.lower()=="bearer" else ""
    async def user(session,request):
        ctx=await DesktopAuthService(session,settings_obj).authenticate(token(request))
        row=await UserRepository(session).get_by_telegram_id(int(ctx.user.telegram_id))
        if not row: raise IOSAdError("ios_user_not_found",404)
        return row
    def error(exc): return JSONResponse(status_code=getattr(exc,"status_code",400),content={"ok":False,"error":getattr(exc,"code","ios_ad_unavailable")},headers={"Cache-Control":"no-store"})
    @router.get("/api/v3/ios/ad")
    async def listing(request:Request):
        try:
            slot=str(request.query_params.get("slot") or "").strip().lower()
            async with session_factory() as session:
                u=await user(session,request)
                if slot not in AD_PLACEMENTS: raise IOSAdError("course_ad_not_found",404)
                placements=AdPlacementService(session); status=await placements.status(u,placement=slot,client="ios")
                if not status.get("enabled") or (status.get("remaining") is not None and status.get("remaining")<=0): raise IOSAdError("course_ad_not_found",404)
                rule=(await placements.get_settings()).rule(slot)
                if rule.audience==AUDIENCE_FREE_ONLY and has_full_access(resolve_state(u)): raise IOSAdError("course_ad_not_found",404)
                ads=[]
                for ad in await placements.list_for_placement(slot,language=getattr(u,"language",None)):
                    payload=placements.ads.payload(ad); payload["placement"]=slot; payload["skip_after_seconds"]=rule.skip_after_seconds
                    if payload.get("ad_type") in IOS_AD_TYPES: ads.append(payload)
                if placements.ads.media_backup_changed: await session.commit()
            if not ads: raise IOSAdError("course_ad_not_found",404)
            return JSONResponse(content={"ok":True,"ads":ads,"slot":slot,"channel":"ios"},headers={"Cache-Control":"no-store"})
        except (DesktopAuthError,IOSAdError) as exc: return error(exc)
        except Exception: return error(IOSAdError("ios_ad_unavailable",503))
    @router.post("/api/v3/ios/ad/view")
    async def viewed(payload:IOSAdViewRequest,request:Request):
        try:
            placement=normalize_placement(payload.placement)
            async with session_factory() as session:
                u=await user(session,request); level=str(getattr(u,"level",None) or "hsk1").lower()
                result=await AdPlacementService(session).record_view(u,placement=placement,ad_id=payload.ad_id,watched_seconds=payload.watched_seconds,level=level,lesson_order=payload.lesson_order)
                if result.get("error"): raise IOSAdError(str(result["error"]),404)
                await CourseMiniAppAnalyticsService(session).record_server_event(event_name="course_ad_viewed",telegram_id=int(u.telegram_id),user_id=getattr(u,"id",None),source="ios_ad",level=level,lesson_order=payload.lesson_order,payload={"ad_id":payload.ad_id,"placement":placement,"watched_seconds":payload.watched_seconds})
                await session.commit()
            return JSONResponse(content=result,headers={"Cache-Control":"no-store"})
        except (DesktopAuthError,IOSAdError) as exc: return error(exc)
        except Exception: return error(IOSAdError("ios_ad_unavailable",503))
    return router
