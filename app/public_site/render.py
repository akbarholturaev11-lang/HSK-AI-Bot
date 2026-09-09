"""HTML rendering with escaped copy and a single canonical URL inventory."""
import json
import re
from html import escape
from urllib.parse import urlencode, urlsplit

from app.public_site.content import CTA, GUIDES, HOME_PATHS, PAGES

BOT_URL = "https://t.me/darsi_chini_bot"
ATTRIBUTION_KEYS = ("source", "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")


def public_origin(settings_obj):
    # Never trust Host or forwarded headers for canonical URLs or submissions.
    explicit = getattr(settings_obj, "PUBLIC_SITE_URL", "").strip()
    value = explicit or getattr(settings_obj, "MINI_APP_BASE_URL", "")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or (explicit and (parsed.path not in ("", "/") or parsed.query or parsed.fragment))):
        raise ValueError("PUBLIC_SITE_URL must be an HTTPS origin without credentials, path or query")
    return f"https://{parsed.netloc}"


def attribution(params):
    # Only campaign labels; never serialize arbitrary queries, referrers or initData.
    return {key: re.sub(r"[^\w .:+-]", "", str(params.get(key, "")))[:80]
            for key in ATTRIBUTION_KEYS if params.get(key)}


def with_attribution(path, tags):
    return path + ("?" + urlencode(tags) if tags else "")


def structured_data(path, origin):
    page = PAGES[path]
    graph = [
        {"@type": "Organization", "@id": origin + "/#organization", "name": "HSK AI",
         "url": origin + "/", "sameAs": [BOT_URL]},
        {"@type": "WebSite", "@id": origin + "/#website", "name": "HSK AI",
         "alternateName": "HSK AI — омӯзиши забони чинӣ", "url": origin + "/",
         "inLanguage": ["tg", "ru", "uz"], "publisher": {"@id": origin + "/#organization"}},
        {"@type": "SoftwareApplication", "@id": origin + "/#application", "name": "HSK AI",
         "applicationCategory": "EducationalApplication", "operatingSystem": "Telegram",
         "url": origin + "/tj/", "installUrl": BOT_URL, "inLanguage": ["tg", "ru", "uz"],
         "description": PAGES["/tj/"]["intro"], "publisher": {"@id": origin + "/#organization"}},
        {"@type": "WebPage", "@id": origin + path + "#page", "url": origin + path,
         "name": page["title"], "description": page["description"], "inLanguage": page["lang"],
         "isPartOf": {"@id": origin + "/#website"}, "about": {"@id": origin + "/#application"}},
    ]
    if path == "/tj/hsk/":
        for level in range(1, 5):
            graph.append({"@type": "Course", "@id": origin + path + f"#hsk{level}",
                          "name": f"HSK {level}", "url": origin + path + f"#hsk{level}",
                          "description": page["sections"][level - 1][1],
                          "inLanguage": ["tg", "ru", "uz"],
                          "provider": {"@id": origin + "/#organization"}})
    return {"@context": "https://schema.org", "@graph": graph}


def render_page(path, settings_obj, tags=None):
    tags = tags or {}
    page = PAGES[path]
    lang = page["lang"]
    origin = public_origin(settings_obj)
    canonical = origin + path
    esc = escape
    alternates = HOME_PATHS if path in HOME_PATHS.values() else {lang: path}
    hreflang = "".join(f'<link rel="alternate" hreflang="{code}" href="{esc(origin + dest)}">'
                       for code, dest in alternates.items())
    verification = ""
    for field, name in (("GOOGLE_SITE_VERIFICATION", "google-site-verification"),
                        ("BING_SITE_VERIFICATION", "msvalidate.01")):
        token = getattr(settings_obj, field, "").strip()
        if token:
            verification += f'<meta name="{name}" content="{esc(token)}">'
    nav = "".join(f'<a lang="{code}" href="{esc(with_attribution(dest, tags))}">{label}</a>'
                  for code, dest, label in (("tg", "/tj/", "Тоҷикӣ"), ("ru", "/ru/", "Русский"), ("uz", "/uz/", "O‘zbekcha")))
    sections = "".join(
        f'<section id="{"hsk" + str(i + 1) if path == "/tj/hsk/" and i < 4 else "section" + str(i + 1)}">'
        f'<h2>{esc(title)}</h2><p>{esc(body)}</p></section>'
        for i, (title, body) in enumerate(page["sections"]))
    guides = "".join(f'<li><a href="{esc(with_attribution(dest, tags))}">{esc(title)}</a></li>'
                     for dest, title in GUIDES.items())
    cta_url = "/go/telegram?" + urlencode({"page": path, **tags})
    cta = f'<a class="cta" href="{esc(cta_url)}" rel="nofollow">{CTA[lang]} <span aria-hidden="true">↗</span></a>'
    labels = {"tg": ("Салом", "Роҳнамоҳо ба тоҷикӣ", "Дар бораи маълумоти ташриф"),
              "ru": ("Привет", "Руководства на таджикском", "О данных посещения"),
              "uz": ("Salom", "Tojik tilidagi qo‘llanmalar", "Tashrif ma’lumotlari haqida")}[lang]
    privacy = {
        "tg": "Мо кушодани саҳифа ва гузариш ба ботро бо нишонаҳои маърака дар сабти сервер ҳисоб мекунем. Ин саҳифа кукиҳои таҳлилӣ намегузорад ва ба ҳисоби Telegram пайваст намекунад.",
        "ru": "Мы записываем открытие страницы и переход к боту с метками кампании в серверный журнал. Страница не устанавливает аналитические cookie и не связывает посещение с аккаунтом Telegram.",
        "uz": "Sahifa ochilishi va botga o‘tish kampaniya belgilari bilan server jurnaliga yoziladi. Sahifa analytics cookie o‘rnatmaydi va tashrifni Telegram hisobiga bog‘lamaydi.",
    }[lang]
    schema = json.dumps(structured_data(path, origin), ensure_ascii=False).replace("<", "\\u003c")
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(page['title'])}</title><meta name="description" content="{esc(page['description'])}">
<link rel="canonical" href="{esc(canonical)}">{hreflang}{verification}
<meta property="og:title" content="{esc(page['title'])}"><meta property="og:description" content="{esc(page['description'])}">
<meta property="og:type" content="website"><meta property="og:url" content="{esc(canonical)}">
<meta property="og:site_name" content="HSK AI"><meta property="og:image" content="{esc(origin)}/public-assets/social-cover.webp">
<meta property="og:image:alt" content="HSK AI"><meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(page['title'])}"><meta name="twitter:description" content="{esc(page['description'])}">
<meta name="twitter:image" content="{esc(origin)}/public-assets/social-cover.webp">
<link rel="icon" href="/public-assets/avatar.webp" type="image/webp">
<link rel="stylesheet" href="/public-assets/site.css?v=1">
<script type="application/ld+json">{schema}</script></head>
<body><header><a class="brand" href="{esc(with_attribution('/', tags))}"><img src="/public-assets/avatar.webp" width="40" height="40" alt="">HSK AI</a><nav aria-label="Language">{nav}</nav></header>
<main><div class="hero"><div><p class="eyebrow">HSK 1–4 · Telegram Mini App</p><h1>{esc(page['h1'])}</h1><p class="intro">{esc(page['intro'])}</p>{cta}<p class="handle"><a href="{esc(cta_url)}" rel="nofollow">@darsi_chini_bot</a></p></div>
<aside class="example" aria-label="中文"><span lang="zh" class="hanzi">你好</span><span class="pinyin">nǐ hǎo</span><span>{labels[0]}</span></aside></div>
<article>{sections}</article><aside class="guides" lang="tg"><h2>{labels[1]}</h2><ul>{guides}</ul></aside>
<div class="closing">{cta}</div></main><footer><span>HSK AI · Тоҷикӣ / Русский / O‘zbekcha</span><details><summary>{labels[2]}</summary><p>{privacy}</p></details></footer></body></html>'''
