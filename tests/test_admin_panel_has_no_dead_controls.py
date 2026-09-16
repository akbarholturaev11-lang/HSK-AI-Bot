"""Admin panelda ishlamaydigan boshqaruv turmasin.

Foydalanuvchi buni aniq aytdi: botda olib tashlangan funksiyalarning
qoldiqlari qolib ketgan va ular odamni chalg'itadi. Adminda bu ayniqsa
qimmat — u boshqaruvni bosadi, "qildim" deb o'ylaydi, lekin hech nima
o'zgarmaydi.

Shu yerda ushlanadigan uchta aniq holat:

1. **Reklama rejimi.** `course_lesson_access_policy` da `ads` rejimi bor edi
   va admin uni tanlay olardi. Reklama ko'rib darsni ochish olib tashlangan,
   ya'ni `active_mode` uni jimgina `subscription` ga aylantiradi: admin
   "reklama bilan ochdim" deb o'ylaydi, o'quvchi esa paywall ko'radi.

2. **Reklama joyi.** Joy endi turdan emas, alohida maydondan olinadi. Yuklash
   formasi uni umuman so'ramasdi — har bir yangi reklama ekran markaziga
   tushardi va dars yakuniga reklama qo'yishning iloji yo'q edi.

3. **Eskirgan yozuvlar.** "Mashq bo'limlarida chiqadi" kabi matnlar mashq
   reklamalari olib tashlangandan keyin shunchaki noto'g'ri.
"""

import re
import unittest
from pathlib import Path

from app.services.entitlements import actions as A
from app.services.entitlements.limits_config import default_config
from app.services.entitlements.state import EntitlementState
from app.services.course_access_policy_service import (
    COURSE_ACCESS_MODE_ADS,
    COURSE_ACCESS_MODE_FREE_UNTIL,
    COURSE_ACCESS_MODE_SUBSCRIPTION,
    COURSE_ACCESS_SELECTABLE_MODES,
)


ADMIN = Path("app/static/admin.html").read_text(encoding="utf-8")
MODULES = Path("app/services/admin_miniapp_service.py").read_text(encoding="utf-8")


class TheAdsModeIsGoneTests(unittest.TestCase):
    def test_the_admin_can_no_longer_choose_the_ads_mode(self):
        self.assertNotIn(COURSE_ACCESS_MODE_ADS, COURSE_ACCESS_SELECTABLE_MODES)
        self.assertIn(COURSE_ACCESS_MODE_SUBSCRIPTION, COURSE_ACCESS_SELECTABLE_MODES)
        self.assertIn(COURSE_ACCESS_MODE_FREE_UNTIL, COURSE_ACCESS_SELECTABLE_MODES)

    def test_the_panel_does_not_offer_it_either(self):
        # Tanlov ro'yxatida `ads` qiymatli variant qolmasin.
        self.assertNotIn('<option value="ads"', ADMIN)

    def test_the_menu_note_no_longer_advertises_it(self):
        self.assertNotIn("Дарс paywall, реклама ёки", MODULES)

    def test_an_old_stored_ads_row_is_explained_rather_than_hidden(self):
        # Eski o'rnatishda saqlangan qiymat bo'lsa, admin nima bo'lganini
        # ko'rishi kerak — jimgina boshqa rejim tanlangandek ko'rinmasin.
        self.assertIn('mode==="ads"', ADMIN)


class TheUploadFormAsksWhereTheAdGoesTests(unittest.TestCase):
    def test_the_form_offers_both_placements(self):
        self.assertIn('data-place="lesson_end"', ADMIN)
        self.assertIn('data-place="screen_center"', ADMIN)

    def test_the_placement_is_sent_with_the_upload(self):
        self.assertIn('fd.append("placements"', ADMIN)

    def test_at_least_one_placement_is_always_sent(self):
        self.assertIn("caPlacementsValue", ADMIN)


class NoStaleCopyTests(unittest.TestCase):
    def test_the_list_does_not_claim_practice_placements(self):
        # Matn faqat izohda qolishi mumkin, ko'rinadigan qatorda emas.
        visible = [
            line
            for line in ADMIN.split("\n")
            if "Mashq bo'limlarida chiqadi" in line and "Ilgari bu yerda" not in line
        ]
        self.assertEqual([], visible)

    def test_the_list_shows_the_real_placement(self):
        self.assertIn("i.placements", ADMIN)


if __name__ == "__main__":
    unittest.main()


class TheLimitPanelCoversEveryEnforcedActionTests(unittest.TestCase):
    """Panelda ko'rinmagan chegara — jimgina o'zgaradigan chegara.

    `save_config` planni BUTUNLAY almashtiradi: panel yubormagan band
    yo'qoladi va harakat jokerga tushadi. Shu sabab `practice.placement`
    birinchi "Saqlash" bosilishida "umrbod"dan "kunlik"ka aylanardi —
    admin buni so'ramagan va hech qayerda ko'rmasdi ham.
    """

    @staticmethod
    def _panel_actions():
        block = ADMIN.split("const LIMIT_ACTIONS=[", 1)[1].split("];", 1)[0]
        return set(re.findall(r'\["([a-z_.*]+)"', block))

    def test_every_action_the_engine_enforces_is_reachable(self):
        panel = self._panel_actions()
        for action in A.ACTIONS:
            with self.subTest(action=action):
                prefix = action.split(".", 1)[0] + ".*"
                self.assertTrue(
                    action in panel or prefix in panel or "*" in panel,
                    f"{action} panelda boshqarilmaydi",
                )

    def test_no_action_is_left_to_a_wildcard_that_would_change_it(self):
        panel = self._panel_actions()
        rules = default_config().plans[EntitlementState.FREE]
        for action in A.ACTIONS:
            if action in panel:
                continue
            own = rules.get(action)
            if own is None:
                continue  # Default ham uni jokerga qoldiradi — farq yo'q.
            prefix = action.split(".", 1)[0] + ".*"
            with self.subTest(action=action):
                self.assertEqual(
                    own.as_dict(),
                    rules[prefix].as_dict(),
                    f"{action} default'da jokerdan farq qiladi, ya'ni panelda o'z qatori bo'lishi kerak",
                )

    def test_the_row_shows_the_rule_actually_in_force(self):
        # Aniq bandi yo'q harakat uchun panel bo'sh maydon emas, amaldagi
        # jokerni ko'rsatadi — aks holda saqlash "Bo'sh maydon qoldi" deb
        # to'xtardi.
        self.assertIn("function limitRule(rules,action)", ADMIN)
        self.assertIn("limitRow(plan,action,label,limitRule(rules,action))", ADMIN)


class EveryAdControlLivesInOneSectionTests(unittest.TestCase):
    """Reklama to'rt joyga bo'linib ketgan edi.

    Foydalanuvchi buni aniq aytdi: "admin panelda 3 ta reklama degan joy bor,
    bu meni chalg'itadi". Modul ro'yxatida `Реклама жойлари`, `App рекламаси`
    va `Реклама кампанияси` alohida tugma edi, roliklar formasi esa
    sozlamalar ichida to'rtinchi joyda turardi — nomlari o'xshash, vazifalari
    boshqa. Endi bitta bo'lim, ichida to'rt tanlov.
    """

    def test_the_menu_offers_exactly_one_ads_entry(self):
        self.assertIn('"key": "ads_hub"', MODULES)
        for gone in ('"key": "ad_placements"', '"key": "app_promo"', '"key": "ads"'):
            with self.subTest(module=gone):
                self.assertNotIn(gone, MODULES)

    def test_the_section_holds_all_four_choices(self):
        for key in ("roliklar", "joylar", "ilova", "bot"):
            with self.subTest(choice=key):
                self.assertIn(f'data-adhub="{key}"', ADMIN)
        for pane in ("adPaneRoliklar", "adPaneJoylar", "adPaneIlova", "adPaneBot"):
            with self.subTest(pane=pane):
                self.assertIn(f'id="{pane}"', ADMIN)

    def test_the_panels_are_not_written_a_second_time(self):
        # Joylar, ilova promosi va kampaniya panellari drawer uchun yozilgan
        # funksiyalarni qayta ishlatadi: `showPanel` ularni bo'lim ichiga
        # chizadi. Ikki nusxa bo'lsa, biri eskirib qolardi.
        self.assertIn("function showPanel(title,sub,html)", ADMIN)
        self.assertIn("panelTarget=cfg.pane", ADMIN)
        self.assertIn("renderAdPlacements(d)", ADMIN)
        self.assertIn("renderAppPromo(d)", ADMIN)
        self.assertIn('renderCampaign(d,"ad")', ADMIN)


class TheUploadFormOnlyAsksWhatTheTypeNeedsTests(unittest.TestCase):
    """Tanlangan turga aloqasi yo'q maydon ko'rinmasin.

    Forma barcha kataklarni birdan ko'rsatardi: "App reklamasi" tanlanmagan
    bo'lsa ham MacBook/Windows/Android havolalari, "X paydo bo'lishi" va
    "Kuniga necha marta" o'sha yerda turardi, "Knopka nomi" esa o'chirilgan
    holda — admin uni ko'rar, lekin nega to'ldira olmasligini bilmasdi.
    """

    def test_the_field_list_is_declared_in_one_place(self):
        self.assertIn("const CA_TYPE_SPEC={", ADMIN)
        for field in ("button", "link", "appLimits", "appLinks"):
            with self.subTest(field=field):
                self.assertIn(f'data-ca-field="{field}"', ADMIN)

    def test_a_field_outside_the_list_is_really_hidden(self):
        # `.frow` grid: brauzerning `[hidden]{display:none}` qoidasi unga
        # yetmaydi, shuning uchun o'z qoidamiz bo'lishi shart.
        self.assertIn("[data-ca-field][hidden]", ADMIN)
        self.assertIn("el.hidden=on.indexOf(el.dataset.caField)<0", ADMIN)

    def test_a_hidden_field_is_not_submitted_anyway(self):
        self.assertIn('caFields.indexOf("button")<0?""', ADMIN)

    def test_the_chosen_placement_chip_looks_chosen(self):
        # `ca-place` chiplari `on` klassini qo'shardi, lekin uni hech qanday
        # CSS qoidasi bo'yamasdi: admin joyni tanlaydi, ekranda esa hech
        # nima o'zgarmasdi.
        self.assertIn(".chip.active,.chip.on{", ADMIN)
