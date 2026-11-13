"""Synthetic scratch-branch fixture; never deployed or registered by the app."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/api/v3/monitoring-guard-fixture")
async def scratch_fixture():
    return JSONResponse({"ok": False}, status_code=502)
