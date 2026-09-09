"""`app/main.py` umuman import bo'ladimi.

Bu testning sababi aniq: 2026-09-08 da production shu xato bilan yiqildi —

    NameError: name '_admin_miniapp_guard' is not defined

`app.include_router(...)` chaqiruvi faylning YUQORISIDA, unga uzatilgan
funksiya esa PASTROQDA e'lon qilingan edi. Modul yuqoridan pastga bajariladi,
shuning uchun bu deploy paytida yiqiladi.

Nega hech qaysi test uni tutmadi: 1100 dan ortiq testning BIRORTASI ham
`app.main` ni import qilmaydi (u botni ishga tushiradi), va `compileall`
faqat sintaksisni tekshiradi — nom bor-yo'qligini emas.

Shu fayl o'sha bo'shliqni yopadi. U hech narsani tekshirmaydi: shunchaki
modulni import qiladi. Import o'tsa, modul darajasidagi har bir nom joyida.
"""

import importlib
import unittest
from unittest.mock import patch


class MainModuleImportTests(unittest.TestCase):
    #: aiogram tokenning SHAKLINI tekshiradi. Haqiqiy token kerak emas —
    #: bu yerda tekshirilayotgan narsa sozlama emas, modul darajasidagi nomlar.
    FAKE_TOKEN = "123456789:AAEhBOweik6ad9r_QXWnRVhTLNRHYlBBBBB"

    @staticmethod
    def _import_main():
        # Sozlama import paytida O'QILADI, shuning uchun `os.environ` ni
        # keyin o'zgartirish kech: `settings` ning o'zi almashtiriladi.
        #
        # QAYTA import qilinmaydi: aiogram routerlari bir marta biriktiriladi
        # va ikkinchi import "Router is already attached" bilan yiqiladi.
        # Jarayondagi BIRINCHI import — haqiqiy tekshiruv.
        from app.config import settings

        with patch.object(
            settings, "BOT_TOKEN", MainModuleImportTests.FAKE_TOKEN
        ), patch.object(settings, "BOT_USERNAME", "hsk_ai_test_bot"):
            return importlib.import_module("app.main")

    def test_the_app_module_imports_without_a_name_error(self):
        module = self._import_main()

        self.assertTrue(hasattr(module, "app"), "FastAPI ilovasi yig'ilishi kerak")

    @staticmethod
    def _paths(routes):
        """Ilovadagi HAMMA yo'l, ichma-ich ulangan routerlar bilan birga.

        FastAPI `include_router` natijasini endi tekis ro'yxatga yoymaydi:
        `app.routes` ichida `.path` i yo'q o'ram obyekt turadi. Faqat yuqori
        qavatga qaralsa, ulanmagan router bilan ulangani bir xil ko'rinadi va
        bu test hech narsani tutmay qoladi.
        """
        paths = set()
        for route in routes:
            path = getattr(route, "path", None)
            if path is not None:
                paths.add(path)
            nested = getattr(route, "routes", None)
            if nested is None:
                # `include_router` o'ram obyekti: haqiqiy router uning ichida.
                nested = getattr(getattr(route, "original_router", None), "routes", None)
            paths.update(MainModuleImportTests._paths(nested or []))
        return paths

    def test_every_router_is_mounted(self):
        module = self._import_main()

        paths = self._paths(module.app.routes)
        # Bu bosqichda qo'shilgan yo'llar — ular ulanmay qolsa jimgina
        # yo'qoladi va hech qanday test qizil bo'lmaydi.
        for path in (
            "/api/v3/practice/daily-gate",
            "/api/v3/trial/start",
            "/api/v3/ad",
            "/api/admin-miniapp/limits/save",
            "/api/admin-miniapp/ad-placements/save",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)


if __name__ == "__main__":
    unittest.main()
