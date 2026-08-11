from pathlib import Path

from playwright.sync_api import expect, sync_playwright


OUT = Path("/Users/kaijimima1234/Desktop/HSK AI bot/output/playwright")
URL = "http://127.0.0.1:8771/?mock=1&goal=hsk"


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 980})
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        page.goto(URL)
        page.wait_for_load_state("networkidle")
        expect(page.locator("#workspace")).to_be_visible(timeout=10000)
        page.locator("#show-practice").click()
        expect(page.locator(".practiceGrid .practiceCard").first).to_be_visible(timeout=10000)
        page.locator(".practiceGrid .practiceGo").first.click()
        expect(page.locator(".practice-question")).to_be_visible(timeout=10000)
        expect(page.locator(".practice-options button").first).to_be_visible(timeout=10000)
        page.screenshot(path=str(OUT / "desktop-practice-open-smoke.png"), full_page=True)
        browser.close()

    serious = [msg for msg in errors if "favicon" not in msg.lower()]
    if serious:
        raise AssertionError("\n".join(serious))
    print("desktop practice open smoke passed")


if __name__ == "__main__":
    main()
