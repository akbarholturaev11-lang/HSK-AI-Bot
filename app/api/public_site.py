"""Unauthenticated marketing routes with anonymous aggregate traffic counts only."""
import json
import logging
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response

from app.public_site.account_deletion_render import render_account_deletion
from app.public_site.content import DOWNLOAD_PATH, GOOGLE_SIGNIN_PRIVACY_PAGES, HOME_PATHS, PAGES
from app.public_site.render import (
    BOT_URL,
    attribution,
    public_origin,
    render_google_signin_privacy,
    render_page,
)
from app.services.public_site_analytics_service import (
    PublicSiteAnalyticsService,
    normalize_public_site_source,
)

logger = logging.getLogger("uvicorn.error.public_analytics")
STATIC = Path(__file__).resolve().parents[1] / "static"
GOOGLE_VERIFICATION_FILENAME = "google4575dc78c69e5824.html"
GOOGLE_VERIFICATION_CONTENT = b"google-site-verification: google4575dc78c69e5824.html"
SITEMAP_PATHS = tuple(PAGES) + (DOWNLOAD_PATH, "/privacy", "/terms", "/account-deletion") + tuple(GOOGLE_SIGNIN_PRIVACY_PAGES)


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
            "urlList": [origin + path for path in SITEMAP_PATHS]}


def sitemap_xml(origin):
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in SITEMAP_PATHS:
        SubElement(SubElement(root, "url"), "loc").text = origin + path
    # No fabricated lastmod; use actual editorial dates if maintained later.
    return tostring(root, encoding="utf-8", xml_declaration=True)


def robots_text(origin):
    # Exact allowlist: newly added private routes stay excluded by default.
    rules = ["Disallow: /", "Allow: /$", "Allow: /?*"]
    for path in PAGES:
        if path != "/":
            rules.extend([f"Allow: {path}$", f"Allow: {path}?*"])
    for path in GOOGLE_SIGNIN_PRIVACY_PAGES:
        rules.extend([f"Allow: {path}$", f"Allow: {path}?*"])
    rules.extend([
        f"Allow: {DOWNLOAD_PATH}$",
        f"Allow: {DOWNLOAD_PATH}?*",
        f"Allow: /{GOOGLE_VERIFICATION_FILENAME}$",
        "Allow: /public-assets/",
        "Allow: /desktop-download$",
        "Allow: /desktop-download?*",
        "Allow: /desktop-download.html$",
        "Allow: /desktop-download.html?*",
        "Allow: /desktop-download-page.css$",
        "Allow: /desktop-download-page.js$",
        "Allow: /assets/",
        "Allow: /privacy$",
        "Allow: /privacy?*",
        "Allow: /account-deletion$",
        "Allow: /account-deletion?*",
        "Allow: /terms$",
        "Allow: /terms?*",
        "Allow: /sitemap.xml$",
        "Allow: /robots.txt$",
    ])
    return "\n\n".join("User-agent: " + agent + "\n" + "\n".join(rules)
                          for agent in ("*", "Googlebot", "Bingbot", "OAI-SearchBot")) + f"\n\nSitemap: {origin}/sitemap.xml\n"


def record_event(name, path, tags):
    logger.info("public_site_event %s", json.dumps(
        {"event": name, "page": path, "attribution": tags}, ensure_ascii=False, separators=(",", ":")))


async def record_attributed_source_visit(request, session_factory):
    tags = attribution(request.query_params)
    source = normalize_public_site_source(tags.get("utm_source") or tags.get("source"))
    if not source or session_factory is None:
        return
    try:
        async with session_factory() as session:
            await PublicSiteAnalyticsService(session).record_source_visit(source)
    except Exception as error:
        logger.warning("public site source count could not be saved: %s", type(error).__name__)


def create_public_site_router(*, settings_obj, session_factory=None):
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
            if path in HOME_PATHS.values():
                await record_attributed_source_visit(request, session_factory)
        return HTMLResponse(render_page(path, settings_obj, tags), headers={
            "Cache-Control": "no-cache", "Content-Language": PAGES[path]["lang"],
            "Referrer-Policy": "strict-origin-when-cross-origin", "X-Content-Type-Options": "nosniff",
        })

    for path in PAGES:
        router.add_api_route(path, landing, methods=["GET", "HEAD"], name="public_" + path.replace("/", "_"))

    @router.get("/privacy")
    async def privacy_policy():
        # Public legal notice used by Android Settings and the Play store listing.
        # It must not require authentication, JavaScript, or a database session.
        body = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>HSK AI Privacy Policy</title><meta name="robots" content="index,follow">
<style>
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;max-width:760px;margin:32px auto;padding:0 20px 40px;line-height:1.65;color:#211d17;background:#fcfaf7}
h1,h2{line-height:1.25}h1{font-size:clamp(1.7rem,5vw,2.2rem)}h2{font-size:1.25rem;margin-top:1.6em}
a{color:#8b3929;overflow-wrap:anywhere}a:focus-visible{outline:2px solid #8b3929;outline-offset:3px}
small{color:#59534c}li{margin:0.45em 0}nav.legal-links{display:flex;flex-wrap:wrap;gap:12px 18px;margin-top:32px;padding-top:20px;border-top:1px solid #d8d0c5}
</style></head><body><main>
<h1>HSK AI Privacy Policy</h1>
<p><small>Effective date: 3 November 2026</small></p>
<h2>Who operates HSK AI</h2>
<p>Pomp HSK AI operates HSK AI, a Chinese-learning service available through its Android app, Telegram bot and Mini App, desktop clients and website. This policy explains what information we process, why we use it, who may receive it, and how you can request deletion. Questions about privacy can be sent to <a href="mailto:hskaiapp@gmail.com">hskaiapp@gmail.com</a> or through <a href="https://t.me/hskai_support_bot">the official HSK AI Support bot</a>.</p>
<h2>Information we collect and use</h2>
<ul>
<li><strong>Account and profile:</strong> Your chosen Telegram, Google or Apple sign-in identifier, linked identity information, any email and name supplied by that provider, profile display name or avatar choice, language and HSK level, and authentication or session records. Google or Apple can create an account without Telegram; equal email addresses do not merge unrelated accounts.</li>
<li><strong>Learning activity:</strong> Lesson and quiz answers, scores, completed lessons, mistakes, XP, streaks, vocabulary practice, study preferences and progress. We use these records to provide lessons, feedback and progress across devices.</li>
<li><strong>AI, images and speech:</strong> Text questions, photos, voice/audio you choose to submit, transcripts, learning feedback and any support or AI-response reports you submit. These inputs are processed to answer your questions, perform transcription or pronunciation evaluation, and handle reports. Please do not include passwords, identity documents or unnecessary sensitive details.</li>
<li><strong>Payments and invitations:</strong> Plan and entitlement status, referrals, eligibility and usage limits, and, when you submit a manual payment, its amount, receipt and review status. The current Google Play build does not collect manual payment receipts in-app.</li>
<li><strong>Devices and diagnostics:</strong> App/device and session identifiers, push notification tokens where enabled, app version, security or service logs, and error details or screenshots you voluntarily send for troubleshooting.</li>
</ul>
<p>The public website may count visits to the home or download pages by campaign source (for example Instagram or YouTube) in aggregate daily totals, without a visitor cookie or account identifier in those counts. Ordinary network requests may still generate technical hosting or security logs.</p>
<h2>Microphone, photos and notifications</h2>
<p>The microphone is used when you choose pronunciation practice or AI Voice. Photos and audio are submitted only when you initiate a feature that needs them; the feature may send them through HSK AI servers to an AI or speech-processing provider. Android may ask for notification permission for optional study reminders, account updates or payment status. You can change app reminder settings and revoke microphone or notification permission in Android settings.</p>
<h2>Service providers and sharing</h2>
<p>We do not sell personal data. To operate the service, necessary information may be processed by Google, Apple or Telegram for your selected sign-in method; by cloud hosting, database, storage, security and delivery providers; by AI or speech-processing providers for features you initiate; and by push notification services such as Firebase Cloud Messaging when enabled. Support staff may review user-submitted bug reports, payment receipts and AI-response reports. Information may also be disclosed where legally required or necessary to prevent abuse. These providers may process information in other countries. We do not use the daily aggregated website source counts to identify individual visitors.</p>
<h2 id="security">Security</h2>
<p>HSK AI uses HTTPS for supported network connections, access controls and account-bound authentication to limit access to user information. Provider account identifiers are protected through keyed hashing where supported by the account integration. No internet service can guarantee absolute security.</p>
<h2>Retention and deletion</h2>
<p>Account, learning and entitlement records are kept while needed to provide the service or until a verified account deletion request is processed, subject to the exceptions below. Transient AI or voice processing, delivery records and operational/security logs may have different technical lifetimes; we do not promise that every external processor deletes inputs immediately.</p>
<p>You can request deletion inside HSK AI or from the public <a href="/account-deletion">account deletion page</a> without reinstalling the app. After identity verification and explicit confirmation, we aim to complete a request within 30 days. The request covers linked sign-in identities, profile, sessions/devices, learning progress, mistakes and voice activity across the shared HSK AI account. Uninstalling the app or unlinking a device does not delete the account.</p>
<p>Pending and rejected manual-payment records are removed as part of account deletion. Approved payment and accounting records, and required partner-payout or ledger evidence, may be retained when needed for financial, legal, security or fraud-prevention obligations. These exceptions and any applicable periods are reviewed on request through support; they are not a reason to keep an otherwise deleted learning account active. External app-store subscriptions must be cancelled separately in the relevant store.</p>
<h2>Your choices and questions</h2>
<p>You can change your profile and study settings, stop using optional AI/voice features, disable reminders, revoke device permissions, sign out, or unlink a provider while another remains available. Contact <a href="mailto:hskaiapp@gmail.com">hskaiapp@gmail.com</a> for questions about access, correction, retention or deletion of your information; you can also use <a href="/account-deletion">the account deletion request page</a>.</p>
<h2>Changes to this policy</h2>
<p>We may revise this policy as the application changes. The effective date at the top identifies this version; material changes will be reflected here and communicated through the service when appropriate.</p>
<nav class="legal-links" aria-label="HSK AI legal and support links"><a href="/">HSK AI</a><a href="/privacy#security">Security</a><a href="/account-deletion">Account Deletion</a><a href="/privacy/google-sign-in/">Google Sign-In Privacy</a><a href="/terms">Terms of Use</a><a href="https://t.me/hskai_support_bot">Support</a></nav>
</main></body></html>"""
        return HTMLResponse(body, headers={
            "Cache-Control": "public, max-age=300",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        })

    @router.get("/account-deletion")
    async def account_deletion():
        return HTMLResponse(render_account_deletion(), headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        })

    @router.get("/terms")
    async def terms_of_use():
        body = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HSK AI Terms of Use</title><meta name="robots" content="index,follow">
<style>body{font-family:system-ui,-apple-system,sans-serif;max-width:760px;margin:40px auto;padding:0 20px;line-height:1.6;color:#211d17}h1,h2{line-height:1.2}small{color:#6c655c}nav.legal-links{display:flex;flex-wrap:wrap;gap:12px 18px;margin-top:32px;padding-top:20px;border-top:1px solid #d8d0c5}a{color:#8b3929}</style></head>
<body><h1>HSK AI Terms of Use</h1><small>Effective: 17 October 2026</small>
<p>By using HSK AI you agree to use the service lawfully and only for its intended learning, account and community features.</p>
<h2>Accounts</h2>
<p>You may create an HSK AI account with Telegram, Google or Apple where offered. You are responsible for access to that sign-in method. Add another method from the account's settings; matching email addresses do not merge accounts. You cannot disconnect the last sign-in method.</p>
<h2>Learning and AI features</h2>
<p>AI-generated explanations, pronunciation feedback and other automated outputs can contain mistakes. They are study aids and should not be treated as professional advice.</p>
<h2>Subscriptions and free access</h2>
<p>Available plans, free limits and included features are shown in the app before purchase. Access may differ by distribution channel and region.</p>
<p>Pro subscriptions and the separate one-time HSK 3.0 unlock belong to your HSK AI account, independently of its sign-in method. The website-distributed Android app and desktop use the existing manual payment and receipt review. The current Google Play app has no purchase flow and reads the access already held by the same HSK AI account.</p>
<h2>Acceptable use</h2>
<p>Do not abuse the service, bypass limits, interfere with other users, automate harmful traffic, or upload content you do not have the right to use.</p>
<h2>Availability</h2>
<p>Features may change as HSK AI is improved. We may suspend access when needed for security, legal compliance, fraud prevention or service integrity.</p>
<h2>Privacy</h2>
<p>How account, learning and device data is handled is described in the HSK AI Privacy Policy.</p>
<h2>Contact</h2>
<p>Use the Support item inside HSK AI or the official HSK AI Support bot <a href="https://t.me/hskai_support_bot">@hskai_support_bot</a>.</p>
<nav class="legal-links" aria-label="HSK AI legal and support links"><a href="/">HSK AI</a><a href="/privacy">Privacy Policy</a><a href="/privacy#security">Security</a><a href="/account-deletion">Account Deletion</a><a href="/privacy/google-sign-in/">Google Sign-In Privacy</a><a href="https://t.me/hskai_support_bot">Support</a></nav>
</body></html>"""
        return HTMLResponse(
            body,
            headers={
                "Cache-Control": "public, max-age=300",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )

    async def google_signin_privacy(request: Request):
        path = request.url.path
        return HTMLResponse(render_google_signin_privacy(path, settings_obj), headers={
            "Cache-Control": "no-cache", "Content-Language": GOOGLE_SIGNIN_PRIVACY_PAGES[path]["lang"],
            "Referrer-Policy": "strict-origin-when-cross-origin", "X-Content-Type-Options": "nosniff",
        })

    for path in GOOGLE_SIGNIN_PRIVACY_PAGES:
        router.add_api_route(path, google_signin_privacy, methods=["GET", "HEAD"], name="privacy_" + path.replace("/", "_"))

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
              "navigation.css": (STATIC / "public-site-navigation.css", "text/css"),
              "language.js": (STATIC / "public-site-language.js", "application/javascript"),
              "account-deletion.js": (STATIC / "account-deletion.js", "application/javascript"),
              "avatar.webp": (STATIC / "assets/hsk-ai-avatar.webp", "image/webp"),
              "logo.png": (STATIC / "assets/hsk-ai-logo-256.png", "image/png"),
              "social-cover.webp": (STATIC / "assets/hsk-ai-cover.webp", "image/webp")}

    @router.get("/public-assets/{filename}")
    async def asset(filename: str):
        if filename not in assets:
            return Response(status_code=404)
        path, media_type = assets[filename]
        return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})

    return router
