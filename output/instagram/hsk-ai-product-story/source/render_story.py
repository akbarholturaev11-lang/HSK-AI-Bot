from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


SOURCE_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = SOURCE_ROOT.parent
STORY_FILE = SOURCE_ROOT / "story.html"


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1,
            locale="tg-TJ",
            color_scheme="light",
        )
        page = context.new_page()

        for card in range(1, 10):
            page.goto(f"{STORY_FILE.as_uri()}?card={card}", wait_until="load")
            page.wait_for_function("Array.from(document.images).every(image => image.complete)")
            page.wait_for_timeout(150)
            page.screenshot(
                path=str(OUTPUT_ROOT / f"hsk-ai-tj-story-{card:02d}.png"),
                full_page=False,
            )

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
