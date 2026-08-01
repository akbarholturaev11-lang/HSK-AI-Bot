from __future__ import annotations

import base64
import logging
from typing import Annotated, Callable, Literal, TypeVar

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    ValidationError,
)

from app.services.desktop_auth_service import DesktopAuthError
from app.services.desktop_subscription_service import (
    DESKTOP_SUBSCRIPTION_STAGES,
    DesktopSubscriptionError,
    DesktopSubscriptionService,
)
from app.services.subscription_miniapp_service import MAX_SCREENSHOT_BYTES


logger = logging.getLogger(__name__)
MAX_DESKTOP_SUBSCRIPTION_BODY_BYTES = 32 * 1024
MAX_SCREENSHOT_BASE64_CHARS = ((MAX_SCREENSHOT_BYTES + 2) // 3) * 4
MAX_SCREENSHOT_DATA_URL_CHARS = MAX_SCREENSHOT_BASE64_CHARS + 40
MAX_DESKTOP_SUBSCRIPTION_SUBMIT_BODY_BYTES = (
    MAX_SCREENSHOT_DATA_URL_CHARS + 16 * 1024
)
PayloadModel = TypeVar("PayloadModel", bound=BaseModel)

DesktopPlan = Literal["10_days", "1_month", "3_months"]
DesktopPaymentMethod = Literal["visa", "alipay", "wechat"]
DesktopCardCountry = Literal["tj", "uz", "ru", "other"]
DesktopAttemptId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=16,
        max_length=80,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
]
DesktopScreenshotDataUrl = Annotated[
    str,
    StringConstraints(
        min_length=32,
        max_length=MAX_DESKTOP_SUBSCRIPTION_SUBMIT_BODY_BYTES,
    ),
]


class DesktopSubscriptionEmptyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DesktopSubscriptionQuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_type: DesktopPlan
    payment_method: DesktopPaymentMethod
    card_country: DesktopCardCountry | None = None


class DesktopSubscriptionEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: DesktopAttemptId
    stage: Literal[
        "payment_instructions_viewed",
        "payment_receipt_selected",
    ]
    plan_type: DesktopPlan
    payment_method: DesktopPaymentMethod


class DesktopSubscriptionSubmitRequest(DesktopSubscriptionQuoteRequest):
    screenshot_data_url: DesktopScreenshotDataUrl
    attempt_id: DesktopAttemptId | None = None


def _access_token(request: Request) -> str:
    value = str(request.headers.get("Authorization", "") or "")
    scheme, separator, token = value.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


async def _validated_payload(
    request: Request,
    model_type: type[PayloadModel],
    *,
    max_body_bytes: int = MAX_DESKTOP_SUBSCRIPTION_BODY_BYTES,
) -> PayloadModel:
    content_type = str(request.headers.get("Content-Type", "") or "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise DesktopSubscriptionError(
            "desktop_subscription_request_invalid",
            status_code=415,
        )

    content_length = str(request.headers.get("Content-Length", "") or "").strip()
    if content_length:
        try:
            parsed_length = int(content_length)
        except ValueError as exc:
            raise DesktopSubscriptionError(
                "desktop_subscription_request_invalid",
                status_code=400,
            ) from exc
        if parsed_length < 0:
            raise DesktopSubscriptionError(
                "desktop_subscription_request_invalid",
                status_code=400,
            )
        if parsed_length > max_body_bytes:
            raise DesktopSubscriptionError(
                "desktop_subscription_request_too_large",
                status_code=413,
            )

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_body_bytes:
            raise DesktopSubscriptionError(
                "desktop_subscription_request_too_large",
                status_code=413,
            )
    try:
        return model_type.model_validate_json(bytes(body))
    except (ValidationError, ValueError, TypeError) as exc:
        raise DesktopSubscriptionError(
            "desktop_subscription_request_invalid",
            status_code=422,
        ) from exc


def _validate_receipt_data_url(value: str) -> None:
    prefix, separator, raw_base64 = str(value or "").partition(",")
    mime_by_prefix = {
        "data:image/jpeg;base64": "jpeg",
        "data:image/jpg;base64": "jpeg",
        "data:image/png;base64": "png",
        "data:image/webp;base64": "webp",
    }
    image_kind = mime_by_prefix.get(prefix)
    if not separator or not image_kind or not raw_base64:
        raise DesktopSubscriptionError("invalid_screenshot", status_code=422)
    if (
        len(raw_base64) > MAX_SCREENSHOT_BASE64_CHARS
        or len(value) > MAX_SCREENSHOT_DATA_URL_CHARS
    ):
        raise DesktopSubscriptionError(
            "desktop_subscription_request_too_large",
            status_code=413,
        )
    try:
        decoded = base64.b64decode(raw_base64, validate=True)
    except Exception as exc:
        raise DesktopSubscriptionError(
            "invalid_screenshot",
            status_code=422,
        ) from exc
    if not decoded:
        raise DesktopSubscriptionError("invalid_screenshot", status_code=422)
    if len(decoded) > MAX_SCREENSHOT_BYTES:
        raise DesktopSubscriptionError(
            "desktop_subscription_request_too_large",
            status_code=413,
        )

    signature_matches = {
        "jpeg": decoded.startswith(b"\xff\xd8\xff"),
        "png": decoded.startswith(b"\x89PNG\r\n\x1a\n"),
        "webp": (
            len(decoded) >= 12
            and decoded.startswith(b"RIFF")
            and decoded[8:12] == b"WEBP"
        ),
    }
    if not signature_matches[image_kind]:
        raise DesktopSubscriptionError("invalid_screenshot", status_code=422)


def _error_response(
    error: DesktopAuthError | DesktopSubscriptionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": error.code},
        headers={"Cache-Control": "no-store"},
    )


def create_desktop_subscription_router(
    *,
    session_factory,
    settings_obj,
    bot,
    service_factory: Callable[..., DesktopSubscriptionService] = (
        DesktopSubscriptionService
    ),
) -> APIRouter:
    router = APIRouter(tags=["desktop-subscription"])

    def service(session) -> DesktopSubscriptionService:
        return service_factory(session, settings_obj, bot=bot)

    @router.get("/api/v3/desktop/subscription/overview")
    async def desktop_subscription_overview(request: Request):
        try:
            if request.query_params:
                raise DesktopSubscriptionError(
                    "desktop_subscription_request_invalid",
                    status_code=422,
                )
            async with session_factory() as session:
                result = await service(session).overview(_access_token(request))
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopSubscriptionError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop subscription overview failed")
            return _error_response(
                DesktopSubscriptionError(
                    "desktop_subscription_unavailable",
                    status_code=503,
                )
            )

    @router.post("/api/v3/desktop/subscription/discount-start")
    async def desktop_subscription_discount_start(request: Request):
        try:
            await _validated_payload(
                request,
                DesktopSubscriptionEmptyRequest,
            )
            async with session_factory() as session:
                result = await service(session).start_discount(
                    _access_token(request)
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopSubscriptionError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop subscription discount start failed")
            return _error_response(
                DesktopSubscriptionError(
                    "desktop_subscription_unavailable",
                    status_code=503,
                )
            )

    @router.post("/api/v3/desktop/subscription/quote")
    async def desktop_subscription_quote(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopSubscriptionQuoteRequest,
            )
            async with session_factory() as session:
                result = await service(session).quote(
                    _access_token(request),
                    plan_type=payload.plan_type,
                    payment_method=payload.payment_method,
                    card_country=payload.card_country,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopSubscriptionError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop subscription quote failed")
            return _error_response(
                DesktopSubscriptionError(
                    "desktop_subscription_unavailable",
                    status_code=503,
                )
            )

    @router.post("/api/v3/desktop/subscription/event")
    async def desktop_subscription_event(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopSubscriptionEventRequest,
            )
            if payload.stage not in DESKTOP_SUBSCRIPTION_STAGES:
                raise DesktopSubscriptionError(
                    "invalid_subscription_stage",
                    status_code=422,
                )
            async with session_factory() as session:
                result = await service(session).record_event(
                    _access_token(request),
                    attempt_id=payload.attempt_id,
                    stage=payload.stage,
                    plan_type=payload.plan_type,
                    payment_method=payload.payment_method,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopSubscriptionError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop subscription event failed")
            return _error_response(
                DesktopSubscriptionError(
                    "desktop_subscription_unavailable",
                    status_code=503,
                )
            )

    @router.post("/api/v3/desktop/subscription/submit")
    async def desktop_subscription_submit(request: Request):
        try:
            payload = await _validated_payload(
                request,
                DesktopSubscriptionSubmitRequest,
                max_body_bytes=MAX_DESKTOP_SUBSCRIPTION_SUBMIT_BODY_BYTES,
            )
            _validate_receipt_data_url(payload.screenshot_data_url)
            async with session_factory() as session:
                result = await service(session).submit(
                    _access_token(request),
                    plan_type=payload.plan_type,
                    payment_method=payload.payment_method,
                    card_country=payload.card_country,
                    screenshot_data_url=payload.screenshot_data_url,
                    attempt_id=payload.attempt_id,
                )
            return JSONResponse(
                content=result,
                headers={"Cache-Control": "no-store"},
            )
        except (DesktopAuthError, DesktopSubscriptionError) as exc:
            return _error_response(exc)
        except Exception:
            logger.exception("Desktop subscription submit failed")
            return _error_response(
                DesktopSubscriptionError(
                    "desktop_subscription_unavailable",
                    status_code=503,
                )
            )

    return router
