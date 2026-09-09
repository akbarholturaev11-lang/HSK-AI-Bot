import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
ADMIN_HANDLER = (ROOT / "app/bot/handlers/admin.py").read_text(encoding="utf-8")
DELETE_SCRIPT = (ROOT / "scripts/delete_user.py").read_text(encoding="utf-8")


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


if __name__ == "__main__":
    unittest.main()
