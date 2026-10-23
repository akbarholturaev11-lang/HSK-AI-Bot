"""HTML rendering with escaped copy and a single canonical URL inventory."""
import json
import re
from html import escape
from urllib.parse import urlencode, urlsplit

from app.public_site.content import (
    CTA,
    DOWNLOAD_CTA,
    DOWNLOAD_PATH,
    GOOGLE_SIGNIN_PRIVACY_PAGES,
    HOME_PATHS,
    NAV_LABELS,
    PAGE_PATHS,
    PAGE_TRANSLATIONS,
    PAGES,
    RELATED_LINKS,
)

BOT_URL = "https://t.me/darsi_chini_bot"
ATTRIBUTION_KEYS = ("source", "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")
LANGUAGE_NAMES = {"tg": "Тоҷикӣ", "ru": "Русский", "uz": "O‘zbekcha"}


def translated_path(path, lang):
    page = PAGES[path]
    group = page.get("translation_group")
    alternates = PAGE_TRANSLATIONS.get(group, {})
    return alternates.get(lang, HOME_PATHS.get(lang, "/"))


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
    lang = page["lang"]
    localized_home = PAGE_TRANSLATIONS["home"].get(lang, "/tj/")
    graph = [
        {"@type": "Organization", "@id": origin + "/#organization", "name": "HSK AI",
         "url": origin + "/", "sameAs": [BOT_URL]},
        {"@type": "WebSite", "@id": origin + "/#website", "name": "HSK AI",
         "alternateName": {"tg": "HSK AI — омӯзиши забони чинӣ",
                           "ru": "HSK AI — изучение китайского языка",
                           "uz": "HSK AI — xitoy tilini o‘rganish"}[lang],
         "url": origin + localized_home,
         "inLanguage": ["tg", "ru", "uz"], "publisher": {"@id": origin + "/#organization"}},
        {"@type": "SoftwareApplication", "@id": origin + "/#application", "name": "HSK AI",
         "applicationCategory": "EducationalApplication", "operatingSystem": ["Android", "macOS", "Windows", "Telegram Mini App"],
         "url": origin + localized_home, "installUrl": origin + DOWNLOAD_PATH, "inLanguage": ["tg", "ru", "uz"],
         "description": PAGES[localized_home]["intro"], "publisher": {"@id": origin + "/#organization"}},
        {"@type": "WebPage", "@id": origin + path + "#page", "url": origin + path,
         "name": page["title"], "description": page["description"], "inLanguage": page["lang"],
         "isPartOf": {"@id": origin + "/#website"}, "about": {"@id": origin + "/#application"}},
    ]
    if page.get("translation_group") == "hsk":
        for level in range(1, 5):
            graph.append({"@type": "Course", "@id": origin + path + f"#hsk{level}",
                          "name": f"HSK {level}", "url": origin + path + f"#hsk{level}",
                          "description": page["sections"][level - 1][1],
                          "inLanguage": ["tg", "ru", "uz"],
                          "provider": {"@id": origin + "/#organization"}})
    if page.get("translation_group") == "guide-faq":
        graph.append({
            "@type": "FAQPage", "@id": origin + path + "#faq",
            "mainEntity": [
                {"@type": "Question", "name": title,
                 "acceptedAnswer": {"@type": "Answer", "text": body}}
                for title, body in page["sections"]
            ],
        })
    return {"@context": "https://schema.org", "@graph": graph}


def render_page(path, settings_obj, tags=None):
    tags = tags or {}
    page = PAGES[path]
    lang = page["lang"]
    origin = public_origin(settings_obj)
    canonical = origin + path
    esc = escape
    group = page.get("translation_group")
    alternates = PAGE_TRANSLATIONS.get(group, {lang: path})
    hreflang = "".join(f'<link rel="alternate" hreflang="{code}" href="{esc(origin + dest)}">'
                       for code, dest in alternates.items())
    verification = ""
    for field, name in (("GOOGLE_SITE_VERIFICATION", "google-site-verification"),
                        ("BING_SITE_VERIFICATION", "msvalidate.01")):
        token = getattr(settings_obj, field, "").strip()
        if token:
            verification += f'<meta name="{name}" content="{esc(token)}">'
    labels = NAV_LABELS[lang]
    nav_paths = (
        ("courses", PAGE_PATHS["hsk"].get(lang, "/tj/hsk/")),
        ("features", PAGE_PATHS["guide-features"].get(lang, "/tj/guide/features/")),
        ("guide", PAGE_PATHS["guide"].get(lang, "/tj/guide/")),
        ("download", with_attribution(DOWNLOAD_PATH, {"lang": "tj" if lang == "tg" else lang})),
    )
    active_nav = (
        "courses" if page.get("translation_group") == "hsk"
        else "features" if page.get("translation_group") == "guide-features"
        else "guide" if str(page.get("translation_group", "")).startswith("guide")
        else None
    )
    aria_current = ' aria-current="page"'
    nav_items = "".join(
        f'<a data-site-nav="{key}" href="{esc(with_attribution(dest, tags) if key != "download" else with_attribution(DOWNLOAD_PATH, {"lang": "tj" if lang == "tg" else lang, **tags}))}"'
        f'{aria_current if key == active_nav else ""}>'
        f'{esc(labels[key])}</a>'
        for key, dest in nav_paths
    )
    nav = "".join(
        f'<a data-site-lang="{code}" lang="{code}" href="{esc(with_attribution(translated_path(path, code), tags))}"'
        f'{aria_current if code == lang else ""}>{label}</a>'
        for code, label in LANGUAGE_NAMES.items()
    )
    sections = "".join(
        f'<section class="content-card" id="{"hsk" + str(i + 1) if group == "hsk" and i < 4 else "section" + str(i + 1)}">'
        f'<h2>{esc(title)}</h2><p>{esc(body)}</p></section>'
        for i, (title, body) in enumerate(page["sections"]))
    related = RELATED_LINKS.get(page.get("content_group"), {}).get(lang, ())
    cards = "".join(
        f'<a class="topic-card" href="{esc(with_attribution(PAGE_PATHS[target][lang], tags))}">'
        f'<span>{esc(title)}</span><p>{esc(description)}</p><span class="card-arrow" aria-hidden="true">↗</span></a>'
        for target, title, description in related
    )
    cta_url = "/go/telegram?" + urlencode({"page": path, **tags})
    cta = f'<a class="cta" href="{esc(cta_url)}" rel="nofollow">{esc(CTA[lang])} <span aria-hidden="true">↗</span></a>'
    course_url = with_attribution(PAGE_PATHS["hsk"][lang], tags)
    primary_label = {"tg": "Курсҳои HSK 1–4", "ru": "Изучить курсы HSK", "uz": "HSK kurslarini ko‘rish"}[lang]
    primary = f'<a class="course-cta" href="{esc(course_url)}">{esc(primary_label)} <span aria-hidden="true">↗</span></a>'
    download_url = with_attribution(DOWNLOAD_PATH, {"lang": "tj" if lang == "tg" else lang, **tags})
    secondary = f'<a data-site-nav="download" class="secondary-cta" href="{esc(download_url)}">{esc(DOWNLOAD_CTA[lang])}</a>'
    language_menu_label = {"tg": "Интихоби забон", "ru": "Выбрать язык", "uz": "Tilni tanlash"}[lang]
    product_titles = {"tg": "HSK AI дар як нигоҳ", "ru": "Что входит в HSK AI", "uz": "HSK AI nimalarni o‘z ichiga oladi"}[lang]
    product_rows = {
        "tg": [("HSK 1–4", "Дарсҳо, луғат ва машқҳо"), ("AI", "Шарҳи калима ва саволу ҷавоб"), ("Android · macOS · Windows", "Барномаҳо ва саҳифаи боргирӣ"), ("Telegram Mini App", "Яке аз роҳҳои истифода")],
        "ru": [("HSK 1–4", "Уроки, словарь и практика"), ("AI", "Разбор слов и ответы на вопросы"), ("Android · macOS · Windows", "Приложения и загрузки"), ("Telegram Mini App", "Дополнительный способ доступа")],
        "uz": [("HSK 1–4", "Darslar, lug‘at va mashqlar"), ("AI", "So‘z izohi va savol-javob"), ("Android · macOS · Windows", "Ilovalar va yuklab olish"), ("Telegram Mini App", "Foydalanish usullaridan biri")],
    }[lang]
    product_rows_html = "".join(f'<div><dt>{esc(term)}</dt><dd>{esc(detail)}</dd></div>' for term, detail in product_rows)
    product_summary = f'<aside class="product-summary" aria-label="{esc(product_titles)}"><p class="eyebrow">HSK AI · PLATFORM</p><h2>{esc(product_titles)}</h2><dl>{product_rows_html}</dl></aside>'
    hero_kicker = {
        "tg": {"guide": "РОҲНАМОИ HSK AI", "default": "HSK 1–4 · ANDROID · DESKTOP · MINI APP"},
        "ru": {"guide": "РУКОВОДСТВО HSK AI", "default": "HSK 1–4 · ANDROID · DESKTOP · MINI APP"},
        "uz": {"guide": "HSK AI QO‘LLANMASI", "default": "HSK 1–4 · ANDROID · DESKTOP · MINI APP"},
    }[lang]["guide" if str(page.get("translation_group", "")).startswith("guide") else "default"]
    nav_aria = {"tg": "Паймоиши асосӣ", "ru": "Основная навигация", "uz": "Asosiy navigatsiya"}[lang]
    section_heading = {
        "tg": "Аз куҷо идома диҳед",
        "ru": "Выберите следующий шаг",
        "uz": "Keyingi qadamni tanlang",
    }[lang]
    privacy = {
        "tg": "Мо кушодани саҳифа ва гузариш ба ботро бо нишонаҳои маърака дар сабти сервер ва омори ҷамъбастии ҳаррӯза ҳисоб мекунем. Ин саҳифа кукиҳои таҳлилӣ намегузорад ва ташрифро ба ҳисоби Telegram пайваст намекунад.",
        "ru": "Мы учитываем открытие страницы и переход к боту с метками кампании в серверном журнале и анонимной дневной статистике. Страница не устанавливает аналитические cookie и не связывает посещение с аккаунтом Telegram.",
        "uz": "Sahifa ochilishi va botga o‘tishni kampaniya belgilari bilan server jurnalida va anonim kunlik jamlanma statistikada hisoblaymiz. Sahifa analytics cookie o‘rnatmaydi va tashrifni Telegram hisobiga bog‘lamaydi.",
    }[lang]
    schema = json.dumps(structured_data(path, origin), ensure_ascii=False).replace("<", "\\u003c")
    body_kind = "guide-page" if str(page.get("translation_group", "")).startswith("guide") else "marketing-page"
    related_section = (
        f'<aside class="related"><h2>{esc(section_heading)}</h2><div class="topic-grid">{cards}</div></aside>'
        if cards else ""
    )
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(page['title'])}</title><meta name="description" content="{esc(page['description'])}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{esc(canonical)}">{hreflang}{verification}
<meta property="og:title" content="{esc(page['title'])}"><meta property="og:description" content="{esc(page['description'])}">
<meta property="og:type" content="website"><meta property="og:url" content="{esc(canonical)}">
<meta property="og:site_name" content="HSK AI"><meta property="og:image" content="{esc(origin)}/public-assets/social-cover.webp?v=2">
<meta property="og:image:alt" content="HSK AI"><meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(page['title'])}"><meta name="twitter:description" content="{esc(page['description'])}">
<meta name="twitter:image" content="{esc(origin)}/public-assets/social-cover.webp?v=2">
<link rel="icon" href="/public-assets/logo.png" type="image/png">
<link rel="stylesheet" href="/public-assets/site.css?v=4">
<link rel="stylesheet" href="/public-assets/navigation.css?v=1">
<script src="/public-assets/language.js?v=1" defer></script>
<script type="application/ld+json">{schema}</script></head>
<body class="public-page {body_kind}"><header class="site-header"><a data-site-nav="home" class="brand" href="{esc(with_attribution(HOME_PATHS[lang], tags))}"><img src="/public-assets/logo.png" width="42" height="42" alt="">HSK AI</a>
<nav class="main-nav" aria-label="{nav_aria}">{nav_items}</nav><details class="language-switch"><summary aria-label="{esc(language_menu_label)}" title="{esc(language_menu_label)}"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-5 5-5 13 0 18M12 3c5 5 5 13 0 18"/></svg><span>{esc(LANGUAGE_NAMES[lang])}</span></summary><div class="language-menu">{nav}</div></details></header>
<main><section class="hero"><div class="hero-copy"><p class="eyebrow">{esc(hero_kicker)}</p><h1>{esc(page['h1'])}</h1><p class="intro">{esc(page['intro'])}</p><div class="actions">{primary}{secondary}</div></div>
{product_summary}</section>
<article class="content-grid">{sections}</article>{related_section}
<div class="closing"><p>{esc({"tg": "Дар Telegram Mini App низ дастрас аст.", "ru": "Также доступно в Telegram Mini App.", "uz": "Telegram Mini App orqali ham foydalanish mumkin."}[lang])}</p>{cta}</div></main><footer class="site-footer"><span>HSK AI · Тоҷикӣ / Русский / O‘zbekcha</span><details><summary>{esc(labels['language'])}: {esc(LANGUAGE_NAMES[lang])}</summary><p>{privacy}</p></details></footer></body></html>'''


def render_google_signin_privacy(path, settings_obj):
    """Render the public Google Sign-In notice without landing-page analytics."""

    page = GOOGLE_SIGNIN_PRIVACY_PAGES[path]
    origin = public_origin(settings_obj)
    canonical = origin + path
    esc = escape
    language_labels = (
        ("/privacy/google-sign-in/tj/", "Тоҷикӣ"),
        ("/privacy/google-sign-in/ru/", "Русский"),
        ("/privacy/google-sign-in/", "O‘zbekcha"),
    )
    language_links = "".join(
        f'<a href="{esc(dest)}">{label}</a>' for dest, label in language_labels
    )
    alternates = "".join(
        f'<link rel="alternate" hreflang="{esc(item["lang"])}" href="{esc(origin + dest)}">'
        for dest, item in GOOGLE_SIGNIN_PRIVACY_PAGES.items()
    )
    sections = "".join(
        f'<section><h2>{esc(title)}</h2><p>{esc(body)}</p></section>'
        for title, body in page["sections"]
    )
    return f'''<!doctype html>
<html lang="{esc(page["lang"])}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(page["title"])}</title><meta name="description" content="{esc(page["description"])}">
<meta name="robots" content="index,follow"><link rel="canonical" href="{esc(canonical)}">{alternates}
<meta property="og:title" content="{esc(page["title"])}"><meta property="og:description" content="{esc(page["description"])}">
<meta property="og:type" content="website"><meta property="og:url" content="{esc(canonical)}"><meta property="og:site_name" content="HSK AI">
<link rel="icon" href="/public-assets/logo.png" type="image/png"><link rel="stylesheet" href="/public-assets/site.css?v=3"></head>
<body class="public-page legal-page"><header class="site-header"><a class="brand" href="/"><img src="/public-assets/logo.png" width="40" height="40" alt="">HSK AI</a><nav class="language-switch" aria-label="Language">{language_links}</nav></header>
<main><article><p class="eyebrow">HSK AI · GOOGLE SIGN-IN</p><h1>{esc(page["h1"])}</h1><p class="intro">{esc(page["intro"])}</p>{sections}</article></main>
<footer><span>HSK AI · {esc(page["title"])} · {esc(page["updated"])}</span></footer></body></html>'''
