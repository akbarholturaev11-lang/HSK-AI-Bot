import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
ADMIN_HANDLER = (ROOT / "app/bot/handlers/admin.py").read_text(encoding="utf-8")
DELETE_SCRIPT = (ROOT / "scripts/delete_user.py").read_text(encoding="utf-8")
USER_REPO = (ROOT / "app/repositories/user_repo.py").read_text(encoding="utf-8")
ADMIN_UI = (ROOT / "app/static/admin.html").read_text(encoding="utf-8")


class AdminDeleteSafetyTest(unittest.TestCase):
    def test_admin_miniapp_delete_refuses_admin_accounts(self):
        block = MAIN.split('async def admin_miniapp_user_delete', 1)[1].split(
            '@app.post("/api/admin-miniapp/users/block")', 1
        )[0]
        self.assertIn("_is_admin_id(target_id)", block)
        self.assertIn("cannot_delete_admin", block)

    def test_admin_miniapp_delete_invalidates_block_cache(self):
        block = MAIN.split('async def admin_miniapp_user_delete', 1)[1].split(
            '@app.post("/api/admin-miniapp/users/block")', 1
        )[0]
        self.assertIn("invalidate_block_cache(target_id)", block)

    def test_bot_deleteuser_refuses_admin_accounts(self):
        self.assertIn("from app.services.blocked_user_guard import invalidate as invalidate_block_cache", ADMIN_HANDLER)
        self.assertGreaterEqual(ADMIN_HANDLER.count("_is_admin(target_id)"), 2)
        self.assertIn("Admin akkauntni o'chirib bo'lmaydi", ADMIN_HANDLER)
        self.assertIn("invalidate_block_cache(target_id)", ADMIN_HANDLER)

    def test_manual_delete_script_refuses_admin_accounts(self):
        self.assertIn("settings.admin_id_list", DELETE_SCRIPT)
        self.assertIn("Refusing to delete admin user", DELETE_SCRIPT)

    def test_repository_delete_covers_modern_account_state(self):
        block = USER_REPO.split("async def delete_by_telegram_id", 1)[1].split(
            "async def set_blocked", 1
        )[0]
        for token in (
            "AccountNoticeDelivery",
            "AndroidPushToken",
            "AssistantConversation",
            "BotOutboundEvent",
            "BotReachabilityEvent",
            "CourseMistakeTarget",
            "CourseTrackState",
            "CourseUserNotification",
            "CourseWordMastery",
            "DesktopDevice",
            "DesktopLinkRequest",
            "DesktopSession",
            "EntitlementShadowEvent",
            "TrialRiskEvent",
            "UserClientPresence",
            "AppPromoState",
            "UserIdentity",
        ):
            self.assertIn(token, block)
        self.assertIn("get_by_telegram_id_for_update", block)
        self.assertIn("User.referred_by_telegram_id", block)
        self.assertIn("User.referrer_id", block)

    def test_repository_delete_preserves_but_anonymizes_financial_ledger(self):
        block = USER_REPO.split("async def delete_by_telegram_id", 1)[1].split(
            "async def set_blocked", 1
        )[0]
        self.assertIn("PortfolioTransaction", block)
        self.assertIn("anonymous_telegram_id = -uid", block)
        self.assertIn(".values(user_telegram_id=anonymous_telegram_id)", block)
        self.assertIn('Payment.payment_status == "approved"', block)
        self.assertIn("screenshot_file_id=None", block)
        self.assertIn("admin_comment=None", block)
        self.assertIn('Payment.payment_status != "approved"', block)
        self.assertNotIn("(Payment, Payment.user_telegram_id)", block)
        self.assertIn("PartnerReferral", block)

    def test_admin_miniapp_delete_failure_is_reported_without_cache_invalidation(self):
        block = MAIN.split("async def admin_miniapp_user_delete", 1)[1].split(
            '@app.post("/api/admin-miniapp/users/block")', 1
        )[0]
        self.assertIn('"delete_failed"', block)
        self.assertLess(block.index("await session.commit()"), block.index("invalidate_block_cache(target_id)"))
        self.assertIn("logger.exception", block)

    def test_admin_miniapp_delete_ui_has_loading_and_specific_errors(self):
        self.assertIn("cannot_delete_admin", ADMIN_UI)
        self.assertIn("delete_failed", ADMIN_UI)
        self.assertIn("O'chirilmoqda…", ADMIN_UI)
        self.assertIn("Foydalanuvchi to'liq o'chirildi", ADMIN_UI)


if __name__ == "__main__":
    unittest.main()
