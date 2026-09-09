"""Unauthenticated marketing routes. No DB, bot startup or learner mutations."""
import json
import logging
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response

from app.public_site.content import PAGES
from app.public_site.render import BOT_URL, attribution, public_origin, render_page

logger = logging.getLogger("uvicorn.error.public_analytics")
STATIC = Path(__file__).resolve().parents[1] / "static"
GOOGLE_VERIFICATION_FILENAME = "google4575dc78c69e5824.html"
GOOGLE_VERIFICATION_CONTENT = b"google-site-verification: google4575dc78c69e5824.html"


def indexnow_key(settings_obj):
    key = getattr(settings_obj, "INDEXNOW_KEY", "").strip()
    if key and not re.fullmatch(r"[A-Za-z0-9-]{8,128}", key):
        raise ValueError("INDEXNOW_KEY must contain 8–128 letters, digits or hyphens")
    return key


def indexnow_payload(settings_obj):
    origin = public_origin(settings_obj)
    key = indexnow_key(settings_obj)
    if not key:
        raise ValueError("Set INDEXNOW_KEY before submitting")
    return {"host": urlsplit(origin).netloc, "key": key,
            "keyLocation": origin + "/" + key + ".txt",
            "urlList": [origin + path for path in PAGES]}


def sitemap_xml(origin):
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in PAGES:
        SubElement(SubElement(root, "url"), "loc").text = origin + path
    # No fabricated lastmod; use actual editorial dates if maintained later.
    return tostring(root, encoding="utf-8", xml_declaration=True)


def robots_text(origin):
    # Exact allowlist: newly added private routes stay excluded by default.
    rules = ["Disallow: /", "Allow: /$", "Allow: /?*"]
    for path in PAGES:
        if path != "/":
            rules.extend([f"Allow: {path}$", f"Allow: {path}?*"])
    rules.extend(["Allow: /public-assets/", "Allow: /sitemap.xml$", "Allow: /robots.txt$"])
    return "\n\n".join("User-agent: " + agent + "\n" + "\n".join(rules)
                          for agent in ("*", "Googlebot", "Bingbot", "OAI-SearchBot")) + f"\n\nSitemap: {origin}/sitemap.xml\n"


def record_event(name, path, tags):
    logger.info("public_site_event %s", json.dumps(
        {"event": name, "page": path, "attribution": tags}, ensure_ascii=False, separators=(",", ":")))


def create_public_site_router(*, settings_obj):
    router = APIRouter(include_in_schema=False)
    origin = public_origin(settings_obj)
    key = indexnow_key(settings_obj)

    @router.get("/" + GOOGLE_VERIFICATION_FILENAME)
    async def google_search_console_verification():
        # Google requires the exact downloaded file content at the site root.
        # Keep this route public and free of noindex/auth headers.
        return Response(GOOGLE_VERIFICATION_CONTENT, media_type="text/html")

    async def landing(request: Request):
        path = request.url.path
        tags = attribution(request.query_params)
        if request.method == "GET":
            record_event("landing_view", path, tags)
        return HTMLResponse(render_page(path, settings_obj, tags), headers={
            "Cache-Control": "no-cache", "Content-Language": PAGES[path]["lang"],
            "Referrer-Policy": "strict-origin-when-cross-origin", "X-Content-Type-Options": "nosniff",
        })

    for path in PAGES:
        router.add_api_route(path, landing, methods=["GET", "HEAD"], name="public_" + path.replace("/", "_"))

    @router.get("/robots.txt")
    async def robots():
        body = robots_text(origin)
        # IndexNow ownership verification must also be fetchable.
        if key:
            body = body.replace("Disallow: /\n", f"Disallow: /\nAllow: /{key}.txt$\n")
        return PlainTextResponse(body)

    @router.get("/sitemap.xml")
    async def sitemap():
        return Response(sitemap_xml(origin), media_type="application/xml")

    @router.get("/go/telegram")
    async def telegram(request: Request):
        path = request.query_params.get("page", "/")
        if path not in PAGES:
            return Response(status_code=400)
        record_event("telegram_bot_cta_clicked", path, attribution(request.query_params))
        return RedirectResponse(BOT_URL, status_code=302, headers={
            "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow",
            "Referrer-Policy": "no-referrer",
        })

    async def verification():
        return PlainTextResponse(key, headers={"X-Robots-Tag": "noindex"})

    if key:
        router.add_api_route("/" + key + ".txt", verification, methods=["GET"])

    assets = {"site.css": (STATIC / "public-site.css", "text/css"),
              "avatar.webp": (STATIC / "assets/hsk-ai-avatar.webp", "image/webp"),
              "social-cover.webp": (STATIC / "assets/hsk-ai-cover.webp", "image/webp")}

    @router.get("/public-assets/{filename}")
    async def asset(filename: str):
        if filename not in assets:
            return Response(status_code=404)
        path, media_type = assets[filename]
        return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})

    return router
