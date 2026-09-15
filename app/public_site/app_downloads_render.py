"""The download facts, in HTML that needs no JavaScript.

The page above this markup decides what to show by fetching its status and
rewriting the DOM. A search or AI crawler runs none of that, so without this
it reads "Versiya tekshirilmoqda…" and learns nothing about what exists.

So the same facts are rendered server-side: one row per platform with its
version, size and a direct link, plus a `SoftwareApplication` entry each in
JSON-LD. It is deliberately plain — a person who opened the page on the wrong
device uses it to find the right file, which is the same thing a crawler
wants.
"""

from html import escape
from typing import Any
import json


PLATFORM_LABELS = {
    "macos": "macOS",
    "windows": "Windows",
    "android": "Android",
}

PLATFORM_OS = {
    "macos": "macOS",
    "windows": "Windows",
    "android": "Android",
}

HEADINGS = {
    "uz": ("Barcha yuklamalar", "Har bir qurilma uchun oxirgi versiya."),
    "ru": ("Все загрузки", "Последняя версия для каждого устройства."),
    "tj": ("Ҳамаи боргириҳо", "Версияи охирин барои ҳар дастгоҳ."),
}

UNAVAILABLE = {
    "uz": "hali chiqarilmagan",
    "ru": "ещё не выпущено",
    "tj": "ҳанӯз нашр нашудааст",
}


def format_size(size: Any) -> str:
    try:
        value = int(size)
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    return f"{value // 1024} KB"


def downloads_section(status: dict[str, Any], *, origin: str, language: str = "uz") -> str:
    """The visible, script-free list of what can be downloaded."""

    heading, lead = HEADINGS.get(language, HEADINGS["uz"])
    unavailable = UNAVAILABLE.get(language, UNAVAILABLE["uz"])
    rows = []
    for name, label in PLATFORM_LABELS.items():
        entry = status.get("platforms", {}).get(name) or {}
        if entry.get("available") and entry.get("download"):
            meta = " · ".join(
                part
                for part in (entry.get("version"), format_size(entry.get("size")))
                if part
            )
            rows.append(
                "<li>"
                f'<a href="{escape(entry["download"])}" rel="nofollow">'
                f"<b>{escape(label)}</b>"
                f"<span>{escape(meta)}</span>"
                "</a>"
                "</li>"
            )
        else:
            rows.append(
                f'<li class="is-unavailable"><b>{escape(label)}</b>'
                f'<span data-i18n="allUnavailable">{escape(unavailable)}</span></li>'
            )
    return (
        # `data-i18n` so the page's own language switch updates this too. The
        # server renders it in one language because that is what a crawler
        # reads; a person switching languages must not be left with an
        # untranslated block underneath a translated page.
        '<section class="all-downloads" aria-labelledby="all-downloads-title">'
        f'<h2 id="all-downloads-title" data-i18n="allTitle">{escape(heading)}</h2>'
        f'<p data-i18n="allLead">{escape(lead)}</p>'
        f'<ul class="all-downloads-list">{"".join(rows)}</ul>'
        "</section>"
    )


def structured_data(status: dict[str, Any], *, origin: str, page_url: str) -> str:
    """One `SoftwareApplication` per published platform.

    Only published ones are described. Announcing a build that does not exist
    is worse than describing nothing: it is the kind of claim an assistant
    repeats to somebody who then cannot find the file.
    """

    graph: list[dict[str, Any]] = []
    for name, label in PLATFORM_LABELS.items():
        entry = status.get("platforms", {}).get(name) or {}
        if not entry.get("available") or not entry.get("download"):
            continue
        node: dict[str, Any] = {
            "@type": "SoftwareApplication",
            "@id": f"{origin}{page_url}#{name}",
            "name": f"HSK AI — {label}",
            "applicationCategory": "EducationalApplication",
            "operatingSystem": PLATFORM_OS[name],
            "url": origin + page_url,
            "downloadUrl": origin + str(entry["download"]),
            "inLanguage": ["tg", "ru", "uz"],
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        }
        if entry.get("version"):
            node["softwareVersion"] = str(entry["version"])
        size = format_size(entry.get("size"))
        if size:
            node["fileSize"] = size
        graph.append(node)

    if not graph:
        return ""
    payload = json.dumps(
        {"@context": "https://schema.org", "@graph": graph},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    # `</script>` inside a JSON string would end the block early.
    payload = payload.replace("<", "\\u003c")
    return f'<script type="application/ld+json">{payload}</script>'
