"""Canonical admin cards and actions work at mobile and desktop widths."""
import copy
import json

import pytest

from test_miniapp_smoke import (
    admin_finance_payload, admin_management_payload, admin_payload,
    app_url, expect, json_response, open_admin_route, page,
)


def _open(page, width):
    page.set_viewport_size({"width": width, "height": 844})
    errors, requests = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("dialog", lambda dialog: dialog.accept())
    payload = copy.deepcopy(admin_payload())
    template = payload["users"][0]
    payload["users"] = [{**template, "account_id": uid, "id": tid, "name": name,
                         "username": "telegram_learner" if tid else None}
                        for uid, tid, name in ((1, None, "Google learner"), (2, 1, "Telegram learner"),
                                              (3, None, "Apple learner"))]
    page.route("**/api/**", lambda route: json_response(route, {"ok": True}))
    page.route("**/api/admin-miniapp/overview", lambda route: json_response(route, payload))
    page.route("**/api/admin-miniapp/finance-stats", lambda route: json_response(route, admin_finance_payload()))
    page.route("**/api/admin-miniapp/management", lambda route: json_response(route, admin_management_payload()))

    def action(route):
        body = json.loads(route.request.post_data or "{}")
        operation = route.request.url.rsplit("/", 1)[-1]
        requests.append((operation, body))
        assert "user_id" in body and "telegram_id" not in body
        user = next(row for row in payload["users"] if row["account_id"] == int(body["user_id"]))
        if operation == "detail":
            return json_response(route, {"ok": True, "user": user, "payments": []})
        if operation == "block":
            user["status"] = "blocked" if body["blocked"] else "free"
        if operation == "give-access":
            user.update(status="active", payment_status="approved", end_date="01.11.2026 12:00")
        if operation == "delete":
            assert body["confirm"] == str(body["user_id"])
            payload["users"].remove(user)
        return json_response(route, {"ok": True, "duration_days": body.get("duration_days"),
            "end_date": user["end_date"], "status": user["status"]})

    page.route("**/api/admin-miniapp/users/*", action)
    page.route("**/api/admin-miniapp/campaigns/create", lambda route: (
        requests.append(("campaign", json.loads(route.request.post_data or "{}"))),
        json_response(route, {"ok": True}),
    ))
    page.goto(app_url("/admin.html"), wait_until="networkidle")
    open_admin_route(page, "users")
    return errors, requests


@pytest.mark.parametrize("width", [390, 1440])
def test_native_admin_card_grant_block_and_disabled_telegram_actions(page, width):
    errors, requests = _open(page, width)
    card = page.locator('#userList [data-user="1"]')
    expect(card).to_contain_text("Google learner")
    expect(card).to_contain_text("User ID 1")
    expect(card).to_contain_text("Telegram уланмаган")
    expect(page.locator('#userList [data-user="2"]')).to_contain_text("Telegram 1")
    card.click()
    expect(page.locator('#drawer [data-copy="1"]')).to_be_visible()
    page.locator("#drawer summary").filter(has_text="Қўшимча амаллар").click()
    expect(page.locator('#drawer [data-umsg="1"]')).to_be_disabled()
    expect(page.locator('#drawer [data-module="discount"]')).to_have_count(1)
    page.locator("#qaDays").fill("17")
    page.locator('#drawer [data-uaccess="1"]').click()
    expect(page.locator("#toast")).to_contain_text("17 кунлик обуна берилди")
    page.locator('#drawer [data-ublock="1"]').click()
    expect(page.locator('#drawer [data-ublock="1"]')).to_have_attribute("data-blocked", "0")
    page.locator('#drawer [data-ublock="1"]').click()
    expect(page.locator('#drawer [data-ublock="1"]')).to_have_attribute("data-blocked", "1")
    assert ("give-access", {"user_id": 1, "duration_days": 17}) in requests
    assert ("block", {"user_id": 1, "blocked": True}) in requests
    assert ("block", {"user_id": 1, "blocked": False}) in requests
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert not errors


@pytest.mark.parametrize("width", [390, 1440])
def test_personal_discount_uses_native_user_id_and_existing_notification_policy(page, width):
    errors, requests = _open(page, width)
    page.locator('#userList [data-user="1"]').click()
    page.locator("#drawer summary").filter(has_text="Қўшимча амаллар").click()
    page.locator('#drawer [data-module="discount"]').click()
    expect(page.locator("#cmTarget")).to_have_value("1")
    expect(page.locator("#cmNotify")).to_be_enabled()
    expect(page.locator("#cmNotify")).to_be_checked()
    page.locator("#cmTitle").fill("Native personal discount")
    page.locator("#cmText").fill("Account-owned offer")
    page.locator("#cmPercent").fill("25")
    page.locator('[data-cmcreate="discount"]').click()
    expect(page.locator("#toast")).to_contain_text("Кампания яратилди")
    campaign = next(body for operation, body in requests if operation == "campaign")
    assert campaign["target_user_id"] == 1
    assert "target_telegram_id" not in campaign
    assert campaign["notify_enabled"] is True
    assert campaign["percent"] == "25"
    assert not errors


@pytest.mark.parametrize("width", [390, 1440])
def test_linked_telegram_message_and_native_delete_keep_canonical_targets(page, width):
    errors, requests = _open(page, width)
    page.locator('#userList [data-user="2"]').click()
    page.locator("#drawer summary").filter(has_text="Қўшимча амаллар").click()
    page.locator('#drawer [data-umsg="2"]').click()
    page.locator("#umText").fill("Hello Telegram learner")
    page.locator("#umTranslate").uncheck()
    page.locator('#drawer [data-umsend="2"]').click()
    expect(page.locator("#toast")).to_contain_text("Хабар юборилди")
    page.locator('#userList [data-user="3"]').click()
    page.locator("#drawer summary").filter(has_text="Қўшимча амаллар").click()
    page.locator('#drawer [data-module="delete_user"]').click()
    expect(page.locator("#delId")).to_have_value("3")
    page.locator("#delConfirm").fill("3")
    page.locator('#drawer [data-deluser]').click()
    expect(page.locator('#userList [data-user="3"]')).to_have_count(0)
    expect(page.locator('#userList [data-user="2"]')).to_have_count(1)
    assert ("message", {"user_id": 2, "text": "Hello Telegram learner", "translate": False}) in requests
    assert ("delete", {"user_id": 3, "confirm": "3"}) in requests
    assert not errors
