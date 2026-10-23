"""Dedicated browser payment adapter; legacy Telegram authentication is separate."""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _reply
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME
from app.admin_api.pwa_webauthn_transport import _guard_post, _body
from app.admin_api.pwa_payment_review import (
    ExecutePaymentReview, PreparePaymentReview, execute_payment_review, prepare_payment_review,
)
from app.services.admin_payment_review_service import PaymentReviewError

logger = logging.getLogger(__name__)


def create_admin_pwa_payment_review_router(*, settings_obj, session_factory, dispatch=None):
    router = APIRouter(tags=["admin-pwa-payments"])

    async def handle(request, *, execute):
        failure = _guard_post(request, settings_obj)
        if failure is not None:
            return failure
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")
        if not cookie:
            return _reply(401, "admin_pwa_unauthorized")
        body = await _body(request, 4096)
        try:
            model = ExecutePaymentReview if execute else PreparePaymentReview
            command = model.model_validate(body)
        except ValidationError:
            return _reply(400, "admin_pwa_invalid_payload")
        try:
            async with session_factory() as db:
                service = execute_payment_review if execute else prepare_payment_review
                result = await service(db, session_cookie=cookie, request=command, settings_obj=settings_obj)
        except PaymentReviewError as exc:
            return _reply(exc.status, str(exc))
        except Exception:
            logger.exception("Admin PWA payment review unavailable")
            return _reply(503, "admin_pwa_payment_unavailable")
        if execute and dispatch is not None:
            # Financial commit already succeeded. Delivery failure must never
            # make the browser believe the decision rolled back and retry it.
            try:
                if await dispatch(result["review_id"]):
                    result["delivery_status"] = "attempted"
            except Exception:
                logger.exception("Admin PWA payment outbox remains pending/uncertain")
        return JSONResponse(content={"ok": True, **result}, headers=_PRIVATE_HEADERS)

    @router.post("/api/admin/v1/payments/prepare-review")
    async def prepare(request: Request):
        return await handle(request, execute=False)

    @router.post("/api/admin/v1/payments/review")
    async def review(request: Request):
        return await handle(request, execute=True)

    return router
