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
I18N = Path("app/bot/utils/i18n.py").read_text(encoding="utf-8")


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
        # Tanlov endi joy kartasining ichida: `AD_PLACEMENTS` dagi har bir
        # joy o'z kartasini va o'z kalitini oladi.
        self.assertIn('["lesson_end"', ADMIN)
        self.assertIn('["screen_center"', ADMIN)
        self.assertIn('data-ca-place="${esc(key)}"', ADMIN)

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


class Hsk30ReleaseControlTests(unittest.TestCase):
    def test_hsk30_release_is_controlled_from_the_admin_panel(self):
        self.assertIn('id="hsk30Enabled"', ADMIN)
        self.assertIn('data-hsk30save', ADMIN)
        self.assertIn('/api/admin-miniapp/hsk30/settings', ADMIN)
        self.assertIn('OFF → ON', ADMIN)
        self.assertIn('NEW', ADMIN)


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


class MiniAppAdvertisingLivesInOneSectionTests(unittest.TestCase):
    """Mini App reklamasi to'rt joyga bo'linib ketgan edi.

    Foydalanuvchi buni aniq aytdi: "admin panelda 3 ta reklama degan joy bor,
    bu meni chalg'itadi". Modul ro'yxatida `Реклама жойлари`, `App рекламаси`
    va `Реклама кампанияси` alohida tugma edi, roliklar formasi esa
    sozlamalar ichida to'rtinchi joyda turardi.

    Endi bitta bo'lim, ichida ikkita tanlov. Rolik va uning joyi BIR ekranda:
    ular bir-birisiz ishlamaydi (rolik `placements` deydi, joy qoidasi esa
    chiqishini hal qiladi), shuning uchun ularni ikki tanlovga bo'lish
    admin uchun ortiqcha qadam edi.
    """

    def test_the_menu_offers_one_mini_app_ads_entry(self):
        self.assertIn('"key": "ads_hub"', MODULES)
        for gone in ('"key": "ad_placements"', '"key": "app_promo"'):
            with self.subTest(module=gone):
                self.assertNotIn(gone, MODULES)

    def test_the_bot_message_campaign_sits_next_to_the_broadcast_instead(self):
        """Botdagi reklama xabari Mini App reklamasi EMAS.

        Boshqa jadval, boshqa kanal (bot chati), boshqa endpoint — rolik
        tizimi bilan bitta satr ham umumiy kodi yo'q. U reklama bo'limiga
        faqat nomidagi "reklama" so'zi tufayli tushgan edi."""
        broadcast = MODULES.index('"key": "broadcast"')
        campaign = MODULES.index('"key": "ads"')
        self.assertLess(broadcast, campaign)
        self.assertLess(campaign - broadcast, 400, "ikkisi yonma-yon turishi kerak")
        # Nomi qaysi kanalda ishlashini aytadi.
        self.assertIn("Ботдаги реклама хабари", MODULES)

    def test_the_section_holds_both_choices(self):
        for key in ("kurs", "ilova"):
            with self.subTest(choice=key):
                self.assertIn(f'data-adhub="{key}"', ADMIN)
        for pane in ("adPaneKurs", "adPaneIlova"):
            with self.subTest(pane=pane):
                self.assertIn(f'id="{pane}"', ADMIN)

    def test_creative_form_is_separate_from_global_placement_settings(self):
        # Rolikning joy tanlovi formada qoladi, lekin barcha reklamalarga
        # ta'sir qiladigan qoidalar sozlamalar dialogiga ko'chirildi.
        form = ADMIN.split('id="adPaneKurs"', 1)[1].split('id="adPaneIlova"', 1)[0]
        dialog = ADMIN.split('id="adRulesModal"', 1)[1].split('id="scrim"', 1)[0]
        self.assertIn('id="caPlacementBox"', form)
        self.assertNotIn('id="adPlacementsBox"', form)
        self.assertIn('id="adPlacementsBox"', dialog)
        self.assertIn('panelTarget=host.id', ADMIN)
        self.assertIn('state.adHub==="kurs"', ADMIN)

    def test_the_panels_are_not_written_a_second_time(self):
        # Joy va ilova promosi panellari drawer uchun yozilgan funksiyalarni
        # qayta ishlatadi: `showPanel` ularni bo'lim ichiga chizadi. Ikki
        # nusxa bo'lsa, biri eskirib qolardi.
        self.assertIn("function showPanel(title,sub,html)", ADMIN)
        self.assertIn("renderAdPlacements(d)", ADMIN)
        self.assertIn("renderAppPromo(d)", ADMIN)


class AdsSettingsModalTests(unittest.TestCase):
    """Umumiy reklama qoidalari asosiy forma ostida takrorlanmasin."""

    def test_settings_gear_is_in_ad_header(self):
        heading = ADMIN.split('id="adHub"', 1)[1].split('id="adHubTabs"', 1)[0]
        self.assertIn('id="adRulesGear"', heading)
        self.assertIn('data-ad-rules-open', heading)
        self.assertIn('aria-haspopup="dialog"', heading)
        self.assertIn('aria-controls="adRulesModal"', heading)

    def test_rules_use_a_real_accessible_modal_card(self):
        self.assertIn('id="adRulesModal" class="ad-rules-backdrop" hidden', ADMIN)
        self.assertIn('class="ad-rules-dialog" role="dialog" aria-modal="true"', ADMIN)
        self.assertIn('aria-labelledby="adRulesTitle"', ADMIN)
        self.assertIn('class="ad-rules-dialog-body"', ADMIN)
        self.assertIn('class="ad-rules-dialog-footer"', ADMIN)
        self.assertEqual(1, ADMIN.count('data-adplacesave>'))
        self.assertIn('function openAdRulesModal()', ADMIN)
        self.assertIn('function closeAdRulesModal()', ADMIN)

    def test_modal_close_and_accessibility_are_wired(self):
        self.assertIn('if((el=T("[data-ad-rules-open]"))) return openAdRulesModal();', ADMIN)
        self.assertIn('if((el=T("[data-ad-rules-close]"))) return closeAdRulesModal();', ADMIN)
        self.assertIn('if(e.target&&e.target.id==="adRulesModal") return closeAdRulesModal();', ADMIN)
        self.assertIn('if(e.key==="Escape"){e.preventDefault();closeAdRulesModal();return;}', ADMIN)
        self.assertIn('e.key==="Tab"', ADMIN)
        self.assertIn('document.body.classList.add("ads-dialog-open")', ADMIN)
        self.assertIn('document.body.classList.remove("ads-dialog-open")', ADMIN)

    def test_settings_are_only_for_course_ads(self):
        self.assertIn('gear.hidden=state.adHub!=="kurs"', ADMIN)
        self.assertIn('if(state.adHub!=="kurs") closeAdRulesModal()', ADMIN)

    def test_cancel_discards_uncommitted_toggle_values(self):
        self.assertIn('if(state.management){', ADMIN)
        self.assertIn('renderAdPlacements(state.management)', ADMIN)
        self.assertIn('caPlaceWarnUI(); // Bekor qilingan', ADMIN)
        self.assertIn('if(!custom&&adRulesInitiallyCustom&&!confirm(', ADMIN)

    def test_save_refreshes_and_closes_only_on_success(self):
        self.assertIn('.then(async()=>{closeAdRulesModal();await afterModule(', ADMIN)
        self.assertIn('data-adplacesave', ADMIN)
        self.assertIn('"ad_placements"', ADMIN)


class TheUploadFormOnlyAsksWhatTheTypeNeedsTests(unittest.TestCase):
    """Tanlangan turga aloqasi yo'q maydon ko'rinmasin.

    Forma barcha kataklarni birdan ko'rsatardi: "App reklamasi" tanlanmagan
    bo'lsa ham MacBook/Windows/Android havolalari, "X paydo bo'lishi" va
    "Kuniga necha marta" o'sha yerda turardi, "Knopka nomi" esa o'chirilgan
    holda — admin uni ko'rar, lekin nega to'ldira olmasligini bilmasdi.
    """

    def test_the_field_list_is_declared_in_one_place(self):
        self.assertIn("const CA_TYPE_SPEC={", ADMIN)
        for field in ("button", "link"):
            with self.subTest(field=field):
                self.assertIn(f'data-ca-field="{field}"', ADMIN)
        # `appLinks` `app` turi bilan birga ketdi.
        self.assertNotIn('data-ca-field="appLinks"', ADMIN)

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


class TheAdVideoDoesNotOwnTimingOrLimitsTests(unittest.TestCase):
    """Rolik yopish vaqtini ham, kunlik chegarani ham belgilamaydi.

    Forma ikkalasini so'rardi va baza ikkalasini saqlardi, lekin ikkalasi
    ham hech qachon ishlamasdi: reklamani beruvchi ikkala yo'l ham
    `skip_after_seconds` ni joy qoidasidan qayta yozadi, rolik bo'yicha
    kunlik chegarani esa na server, na Mini App, na Android tekshirardi.
    Admin to'ldirar, "qildim" deb o'ylardi, hech nima o'zgarmasdi.
    """

    UPLOAD = Path("app/main.py").read_text(encoding="utf-8")
    ADS = Path("app/services/course_ad_service.py").read_text(encoding="utf-8")
    PLACEMENTS = Path("app/services/ad_placement_service.py").read_text(
        encoding="utf-8"
    )
    ANDROID = Path("app/api/android_features.py").read_text(encoding="utf-8")

    def test_the_form_no_longer_asks_for_them(self):
        self.assertNotIn('id="caSkipAfter"', ADMIN)
        self.assertNotIn('id="caDailyLimit"', ADMIN)
        self.assertNotIn('data-ca-field="appLimits"', ADMIN)

    def test_the_upload_endpoint_no_longer_stores_them(self):
        self.assertNotIn('form.get("skip_after_seconds")', self.UPLOAD)
        self.assertNotIn('form.get("daily_limit")', self.UPLOAD)

    def test_the_payload_does_not_claim_to_own_them(self):
        self.assertNotIn('"skip_after_seconds": cls.normalize_skip_after', self.ADS)
        self.assertNotIn('"daily_limit": cls.normalize_daily_limit', self.ADS)

    def test_the_placement_rule_is_the_only_source(self):
        # Ikkala beruvchi yo'l ham yopish vaqtini joy qoidasidan qo'yadi.
        self.assertIn(
            'payload["skip_after_seconds"] = rule.skip_after_seconds', self.PLACEMENTS
        )
        self.assertIn(
            'payload["skip_after_seconds"] = rule.skip_after_seconds', self.ANDROID
        )
        # Kunlik chegara esa ko'rilgan qatorlardan sanaladi.
        self.assertIn("if rule.daily_cap:", self.PLACEMENTS)
        self.assertIn("used >= rule.daily_cap", self.PLACEMENTS)


class SimplifiedPlacementControlsTests(unittest.TestCase):
    """Rolik uchun joy tanlash va umumiy ko'rsatish qoidasi alohida.

    Ikkala joyga bir xil auditoriya, kunlik limit va yopish vaqtini
    BITTA formadan saqlaymiz, lekin har biri faol/o'chiq bo'lishi mumkin.
    """

    def test_each_ad_chooses_from_exactly_two_placements(self):
        self.assertIn('data-ca-place="${esc(key)}"', ADMIN)
        self.assertIn('id="caPlacementBox"', ADMIN)
        self.assertIn('["lesson_end"', ADMIN)
        self.assertIn('["screen_center"', ADMIN)

    def test_global_rules_have_one_control_for_each_setting(self):
        self.assertEqual(1, ADMIN.count('id="adAudience"'))
        self.assertEqual(1, ADMIN.count('id="adDailyCap"'))
        self.assertEqual(1, ADMIN.count('id="adSkipAfter"'))
        self.assertNotIn('id="adCap_${id}"', ADMIN)
        self.assertNotIn('id="adSkip_${id}"', ADMIN)
        self.assertIn('AD_PLACEMENTS.forEach(([key])=>', ADMIN)
        self.assertIn('skip_after_seconds:skip,', ADMIN)
        self.assertIn('daily_cap:cap,', ADMIN)

    def test_each_place_can_still_be_switched_off(self):
        self.assertIn('id="adOn_${k}"', ADMIN)
        self.assertIn('data-ca-place-warn="${esc(key)}"', ADMIN)
        self.assertIn('caPlaceRules=((d.ad_placements||{}).placements)||{}', ADMIN)

    def test_legacy_differences_are_disclosed(self):
        self.assertIn('const different=fields.some', ADMIN)
        self.assertIn("ikkala joyga bir xil auditoriya", ADMIN.lower())
        self.assertIn("Bu video davomiyligidan BOSHQA sozlama.", ADMIN)

    def test_standard_mode_hides_unneeded_settings(self):
        self.assertIn('id="adCustomMode"', ADMIN)
        self.assertIn('role="switch"', ADMIN)
        self.assertIn('id="adPresetSummary"', ADMIN)
        self.assertIn('id="adCustomSettings"', ADMIN)
        self.assertIn('if(advanced) advanced.hidden=!custom', ADMIN)
        self.assertIn('if(standard) standard.hidden=custom', ADMIN)
        self.assertIn('adRulesModeUI()', ADMIN)

    def test_custom_mode_is_detected_from_saved_backend_rules(self):
        self.assertIn('function adRulesAreCustom(cfg)', ADMIN)
        self.assertIn('adRulesInitiallyCustom=adRulesAreCustom(cfg)', ADMIN)
        self.assertIn('if(!custom&&adRulesInitiallyCustom&&!confirm(', ADMIN)

    def test_preset_matches_conservative_backend_limits(self):
        self.assertIn('daily_cap:1,', ADMIN)
        self.assertIn('skip_after_seconds:5,', ADMIN)
        self.assertIn('audience:"free_only"', ADMIN)
        self.assertIn('enabled:custom?', ADMIN)
        self.assertIn('clients:custom?', ADMIN)

    def test_selection_survives_refresh(self):
        self.assertIn('const caPlaceChosen={lesson_end:true,screen_center:false}', ADMIN)
        self.assertIn('caPlaceChosen[el.dataset.caPlace]=el.checked', ADMIN)

    def test_empty_placement_selection_is_rejected(self):
        self.assertIn('id="caPlaceNone"', ADMIN)
        self.assertIn('return on.join(",")', ADMIN)
        self.assertIn('if(!caPlacementsValue()){ toast(', ADMIN)


class OrdinaryAdCtaContractTests(unittest.TestCase):
    def test_custom_cta_is_available_for_regular_ads(self):
        self.assertIn('odiy:{\n        fields:["link","button"]', ADMIN)
        self.assertIn('buttonLabel:"Tugma nomi (ixtiyoriy)"', ADMIN)
        self.assertIn('const btnLine=(i.button_text)?', ADMIN)
        self.assertIn('fd.append("button_text",caFields.indexOf("button")<0?', ADMIN)


class UserAccessDetailsAreExplicitTests(unittest.TestCase):
    def test_user_detail_separates_access_from_payment(self):
        for label in (
            "Access turi",
            "Sabab",
            "Boshlangan",
            "Tugaydi",
            "Qo'shimcha AI savollar",
            "Taklif qilgan",
            "O'z referral kodi",
            "Faol referral",
        ):
            with self.subTest(label=label):
                self.assertIn(label, ADMIN)

    def test_temporary_access_is_not_called_a_paid_subscription(self):
        self.assertIn('u.status==="active"&&u.payment_status!=="approved"', ADMIN)
        self.assertIn('"Vaqtinchalik access"', ADMIN)
        self.assertIn('(u.payment_status==="approved"?"obuna":"access")+" tugaydi "', ADMIN)

    def test_latest_user_payload_exposes_canonical_entitlement(self):
        for field in ('"access_type"', '"access_label"', '"access_ends_at"'):
            with self.subTest(field=field):
                self.assertIn(field, MODULES)


class ReferralCopyMatchesCurrentBehaviorTests(unittest.TestCase):
    def test_goal_copy_says_six_without_changing_the_reward_constant(self):
        self.assertIn("REFERRAL_TRIAL_REQUIRED_ACTIVE = 5", Path("app/services/referral_service.py").read_text(encoding="utf-8"))
        self.assertIn("+6 ta faol do‘st", I18N)
        self.assertIn("Пригласите +6 активных друзей", I18N)
        self.assertIn("+6 дӯсти фаъол", I18N)
