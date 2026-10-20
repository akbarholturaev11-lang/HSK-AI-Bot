"""Local public-site + installer preview, without production DB/bot or releases.

Run: python -m uvicorn scripts.preview_public_site:app --host 127.0.0.1 --port 8765
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.public_site import create_public_site_router
from app.config import Settings

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
app = FastAPI()
app.include_router(create_public_site_router(settings_obj=Settings(_env_file=None)))

# Preview only. Serve the actual installer HTML/JS/CSS against an unavailable
# release response; never call production release, auth, account or payment APIs.
@app.get("/download")
@app.get("/desktop-download")
@app.get("/desktop-download.html")
async def preview_download():
    return FileResponse(STATIC / "desktop-download.html", media_type="text/html")


@app.get("/desktop-download-page.js")
async def preview_download_script():
    return FileResponse(STATIC / "desktop-download-page.js", media_type="application/javascript")


@app.get("/desktop-download-page.css")
async def preview_download_styles():
    return FileResponse(STATIC / "desktop-download-page.css", media_type="text/css")


@app.get("/api/v3/apps/public-status")
async def preview_release_status():
    return {"ok": True, "platforms": {}}


app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="preview-assets")
