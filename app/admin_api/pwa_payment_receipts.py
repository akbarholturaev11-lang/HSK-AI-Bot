"""Authenticated bounded receipt image delivery; no Telegram URL/token leak."""
import asyncio
import hashlib
import io
import re

from fastapi import APIRouter, Request
from fastapi.responses import Response
from PIL import Image

from app.admin_api.pwa_google_transport import _PRIVATE_HEADERS, _gate, _reply
from app.admin_api.pwa_read import read_transaction
from app.admin_api.pwa_sessions import ADMIN_PWA_COOKIE_NAME, authenticate_admin_pwa_session
from app.repositories.payment_repo import PaymentRepository

_MAX_BYTES = 8 * 1024 * 1024


class _BoundedImage(io.BytesIO):
    def write(self, value):
        if self.tell() + len(value) > _MAX_BYTES:
            raise ValueError("receipt_too_large")
        return super().write(value)


async def download_receipt_image(bot, file_id):
    async with asyncio.timeout(10):
        file = await bot.get_file(file_id)
        if not file.file_path or (file.file_size or 0) > _MAX_BYTES:
            raise ValueError("invalid_receipt_file")
        buffer = _BoundedImage()
        await bot.download_file(file.file_path, destination=buffer, timeout=8)
        raw = buffer.getvalue()
    with Image.open(io.BytesIO(raw)) as image:
        media_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(image.format)
        if media_type is None or image.width * image.height > 20_000_000:
            raise ValueError("invalid_receipt_image")
        image.verify()
    return raw, media_type


def create_admin_pwa_receipt_router(*, settings_obj, session_factory, loader):
    router = APIRouter(tags=["admin-pwa-receipts"])

    @router.get("/api/admin/v1/payments/{payment_id}/receipt")
    async def receipt(request: Request, payment_id: int):
        gate = _gate(request, settings_obj)
        if gate is not None:
            return gate
        if request.headers.get("sec-fetch-site", "same-origin") != "same-origin":
            return _reply(403, "admin_pwa_csrf")
        values = request.query_params.getlist("receipt_sha256")
        if (not 0 < payment_id <= 2_147_483_647 or len(values) != 1
                or set(request.query_params) != {"receipt_sha256"}
                or not re.fullmatch(r"[0-9a-f]{64}", values[0])):
            return _reply(400, "admin_pwa_invalid_payload")
        cookie = request.cookies.get(ADMIN_PWA_COOKIE_NAME, "")

        async def authorized_reference():
            async with session_factory() as db:
                async with read_transaction(db):
                    actor = await authenticate_admin_pwa_session(db, cookie, settings_obj)
                    if actor is None:
                        return None, 401
                    repo = PaymentRepository(db)
                    payment = await repo.get_by_id(payment_id)
                    if (not payment or payment.payment_status != "pending" or not payment.screenshot_file_id
                            or not await repo.get_owner(payment)):
                        return None, 404
                    if hashlib.sha256(payment.screenshot_file_id.encode()).hexdigest() != values[0]:
                        return None, 409
                    return payment.screenshot_file_id, 200
        try:
            reference, status = await authorized_reference()
            if status != 200:
                return _reply(status, "admin_pwa_receipt_unavailable")
            raw, media_type = await loader(reference)
            # Session revocation/payment replacement during network IO must
            # prevent delivering the old image under a new confirmation.
            checked, status = await authorized_reference()
            if status != 200 or checked != reference:
                return _reply(status if status != 200 else 409, "admin_pwa_receipt_unavailable")
        except Exception:
            # Do not log Telegram paths, tokens or image bytes.
            return _reply(503, "admin_pwa_receipt_unavailable")
        return Response(raw, media_type=media_type, headers=_PRIVATE_HEADERS)
    return router
