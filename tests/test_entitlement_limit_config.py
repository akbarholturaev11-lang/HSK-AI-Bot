"""Limit konfiguratsiyasi — ma'lumot sifatida.

Ikki xil xatti-harakat ataylab farq qiladi va shu fayl o'sha farqni qotiradi:

* O'QISHDA (`get_config`) buzilgan JSON, noma'lum holat yoki noma'lum action
  jimgina defaultga tushadi. Sabab: noto'g'ri sozlama butun limit yo'lini
  o'ldirmasligi kerak.
* YOZISHDA (`save_config`) o'sha narsalar `ValueError` bilan rad etiladi.
  Sabab: admin nima yozganini bilishi kerak, jimgina "tuzatilgan" sozlama
  undan ham yomon.
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.entitlements import actions as A
from app.services.entitlements.limits_config import (
    ENTITLEMENT_LIMITS_KEY,
    MAX_LIMIT,
    WINDOW_DAILY,
    WINDOW_LIFETIME,
    WINDOW_NONE,
    LimitConfigService,
    config_from_payload,
    default_config,
)
from app.services.entitlements.state import EntitlementState


class _Repo:
    def __init__(self, stored=None):
        self.stored = stored
        self.set_calls = []

    async def get(self, _key):
        return self.stored

    async def set(self, key, value):
        self.set_calls.append((key, value))
        self.stored = value


def _service(stored=None) -> LimitConfigService:
    service = LimitConfigService(SimpleNamespace(flush=AsyncMock()))
    service.repo = _Repo(stored)
    return service


class DefaultLimitTests(unittest.TestCase):
    def test_the_free_defaults_are_the_agreed_numbers(self):
        config = default_config()
        for action, expected in (
            (A.LESSON_START, 2),
            (A.AI_TEXT, 5),
            (A.AI_VOICE, 2),
            (A.SPEAKING_SESSION, 1),
        ):
            with self.subTest(action=action):
                self.assertEqual(
                    expected, config.limit_for(EntitlementState.FREE, action).limit
                )

    def test_paid_and_temp_access_are_unlimited(self):
        config = default_config()
        for state in (EntitlementState.PRO_ACTIVE, EntitlementState.TEMP_ACCESS):
            for action in A.ACTIONS:
                with self.subTest(state=state, action=action):
                    self.assertTrue(config.limit_for(state, action).unlimited)

    def test_the_trial_is_generous_but_never_unlimited(self):
        # UI da "cheksiz" so'zi faqat `limit is None` bo'lganda chiqadi.
        # Trial hisoblanadigan bo'lib qolishi shart — AI xarajati shunga bog'liq.
        config = default_config()
        for action in A.ACTIONS:
            with self.subTest(action=action):
                rule = config.limit_for(EntitlementState.TRIAL_ACTIVE, action)
                self.assertFalse(rule.unlimited)
                free = config.limit_for(EntitlementState.FREE, action).limit
                self.assertGreaterEqual(rule.limit, free)

    def test_blocked_can_do_nothing(self):
        config = default_config()
        for action in A.ACTIONS:
            with self.subTest(action=action):
                self.assertEqual(0, config.limit_for(EntitlementState.BLOCKED, action).limit)

    def test_expired_inherits_the_free_tier(self):
        config = default_config()
        for action in A.ACTIONS:
            with self.subTest(action=action):
                self.assertEqual(
                    config.limit_for(EntitlementState.FREE, action),
                    config.limit_for(EntitlementState.EXPIRED, action),
                )

    def test_the_prefix_wildcard_covers_every_practice_section(self):
        config = default_config()
        for action in (
            A.PRACTICE_RECOGNITION,
            A.PRACTICE_MEMORIZE,
            A.PRACTICE_MISTAKE_REVIEW,
        ):
            with self.subTest(action=action):
                self.assertEqual(1, config.limit_for(EntitlementState.FREE, action).limit)

    def test_an_exact_rule_beats_the_prefix_wildcard(self):
        # `practice.*` kunlik 1 beradi, `practice.placement` esa umrbod 1.
        config = default_config()
        placement = config.limit_for(EntitlementState.FREE, A.PRACTICE_PLACEMENT)
        self.assertEqual(WINDOW_LIFETIME, placement.window)
        self.assertEqual(
            WINDOW_DAILY,
            config.limit_for(EntitlementState.FREE, A.PRACTICE_RECOGNITION).window,
        )


class BrokenConfigFallsBackTests(unittest.TestCase):
    def test_a_broken_json_string_reads_as_defaults(self):
        # `get_config` JSON ni o'zi parse qiladi; buzilgani defaultga tushadi.
        config = config_from_payload("{{{ not json")
        self.assertEqual(2, config.limit_for(EntitlementState.FREE, A.LESSON_START).limit)

    def test_an_unknown_state_is_ignored(self):
        config = config_from_payload(
            {"plans": {"WAT": {A.LESSON_START: {"limit": 99, "window": WINDOW_DAILY}}}}
        )
        self.assertEqual(2, config.limit_for(EntitlementState.FREE, A.LESSON_START).limit)

    def test_an_unknown_action_is_dropped_but_the_rest_survives(self):
        config = config_from_payload(
            {
                "plans": {
                    EntitlementState.FREE: {
                        "wat.nope": {"limit": 99, "window": WINDOW_DAILY},
                        A.LESSON_START: {"limit": 7, "window": WINDOW_DAILY},
                    }
                }
            }
        )
        self.assertEqual(7, config.limit_for(EntitlementState.FREE, A.LESSON_START).limit)

    def test_an_out_of_range_limit_falls_back_for_that_entry_only(self):
        config = config_from_payload(
            {
                "plans": {
                    EntitlementState.FREE: {
                        A.LESSON_START: {"limit": MAX_LIMIT + 1, "window": WINDOW_DAILY},
                        A.AI_TEXT: {"limit": 9, "window": WINDOW_DAILY},
                    }
                }
            }
        )
        self.assertEqual(2, config.limit_for(EntitlementState.FREE, A.LESSON_START).limit)
        self.assertEqual(9, config.limit_for(EntitlementState.FREE, A.AI_TEXT).limit)

    def test_a_bad_window_falls_back(self):
        config = config_from_payload(
            {
                "plans": {
                    EntitlementState.FREE: {
                        A.LESSON_START: {"limit": 4, "window": "weekly"}
                    }
                }
            }
        )
        self.assertEqual(2, config.limit_for(EntitlementState.FREE, A.LESSON_START).limit)

    def test_an_unknown_action_at_lookup_time_never_raises(self):
        config = default_config()
        rule = config.limit_for(EntitlementState.FREE, "totally.made.up")
        self.assertIsNotNone(rule)

    def test_an_inherit_loop_terminates(self):
        # Ikki holat bir-biriga ishora qilsa ham chaqiruv qotib qolmasin.
        config = config_from_payload(
            {
                "plans": {
                    EntitlementState.FREE: {"*": f"inherit:{EntitlementState.EXPIRED}"},
                    EntitlementState.EXPIRED: {"*": f"inherit:{EntitlementState.FREE}"},
                }
            }
        )
        self.assertIsNotNone(config.limit_for(EntitlementState.FREE, A.LESSON_START))

    def test_null_means_unlimited_and_zero_means_forbidden(self):
        config = config_from_payload(
            {
                "plans": {
                    EntitlementState.FREE: {
                        A.LESSON_START: {"limit": None, "window": WINDOW_DAILY},
                        A.AI_TEXT: {"limit": 0, "window": WINDOW_DAILY},
                    }
                }
            }
        )
        self.assertTrue(config.limit_for(EntitlementState.FREE, A.LESSON_START).unlimited)
        forbidden = config.limit_for(EntitlementState.FREE, A.AI_TEXT)
        self.assertEqual(0, forbidden.limit)
        self.assertEqual(WINDOW_NONE, forbidden.window)


class TrialSettingsTests(unittest.TestCase):
    def test_the_defaults_are_seven_days_and_a_capped_budget(self):
        trial = default_config().trial
        self.assertTrue(trial["enabled"])
        self.assertEqual(7, trial["days"])
        self.assertGreater(trial["ai_budget_usd"], 0)

    def test_the_kill_switch_is_a_plain_flag(self):
        config = config_from_payload(
            {"trial": {"enabled": False, "disabled_reason": "fake akkauntlar"}}
        )
        self.assertFalse(config.trial["enabled"])
        self.assertEqual("fake akkauntlar", config.trial["disabled_reason"])

    def test_out_of_range_trial_values_fall_back(self):
        config = config_from_payload(
            {"trial": {"days": 9999, "ai_budget_usd": -1, "min_account_age_hours": -5}}
        )
        self.assertEqual(7, config.trial["days"])
        self.assertEqual(1.5, config.trial["ai_budget_usd"])
        self.assertEqual(0, config.trial["min_account_age_hours"])


class SaveConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_valid_edit_round_trips_through_the_settings_row(self):
        service = _service()

        await service.save_config(
            {
                "plans": {
                    EntitlementState.FREE: {
                        A.LESSON_START: {"limit": 3, "window": WINDOW_DAILY},
                        A.AI_TEXT: {"limit": 3, "window": WINDOW_DAILY},
                    }
                },
                "trial": {"enabled": True, "days": 14},
            },
            updated_by_telegram_id=777,
        )

        key, _value = service.repo.set_calls[0]
        self.assertEqual(ENTITLEMENT_LIMITS_KEY, key)

        reloaded = await service.get_config()
        self.assertEqual(3, reloaded.limit_for(EntitlementState.FREE, A.LESSON_START).limit)
        self.assertEqual(14, reloaded.trial["days"])
        self.assertEqual(777, reloaded.updated_by_telegram_id)
        # Tegilmagan holatlar default qiymatida qoladi.
        self.assertTrue(
            reloaded.limit_for(EntitlementState.PRO_ACTIVE, A.LESSON_START).unlimited
        )

    async def test_the_stored_row_is_valid_json(self):
        service = _service()
        await service.save_config(
            {"plans": {EntitlementState.FREE: {A.LESSON_START: {"limit": 1, "window": WINDOW_DAILY}}}}
        )
        json.loads(service.repo.set_calls[0][1])

    async def test_an_all_unlimited_free_tier_is_refused(self):
        # Bu deyarli har doim tasodifiy va to'g'ridan-to'g'ri daromadga uradi.
        service = _service()
        with self.assertRaises(ValueError):
            await service.save_config(
                {"plans": {EntitlementState.FREE: {"*": {"limit": None, "window": WINDOW_NONE}}}}
            )
        self.assertEqual([], service.repo.set_calls)

    async def test_unknown_states_actions_and_windows_are_refused(self):
        service = _service()
        bad_payloads = [
            {},
            {"plans": {}},
            {"plans": {"WAT": {A.LESSON_START: {"limit": 1, "window": WINDOW_DAILY}}}},
            {"plans": {EntitlementState.FREE: {"nope.nope": {"limit": 1, "window": WINDOW_DAILY}}}},
            {"plans": {EntitlementState.FREE: {A.LESSON_START: {"limit": 1, "window": "weekly"}}}},
            {"plans": {EntitlementState.FREE: {A.LESSON_START: {"limit": MAX_LIMIT + 1, "window": WINDOW_DAILY}}}},
            {"plans": {EntitlementState.FREE: {A.LESSON_START: {"limit": -1, "window": WINDOW_DAILY}}}},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    await service.save_config(payload)
        self.assertEqual([], service.repo.set_calls)

    async def test_a_missing_settings_row_reads_as_defaults(self):
        self.assertEqual(
            2,
            (await _service().get_config()).limit_for(
                EntitlementState.FREE, A.LESSON_START
            ).limit,
        )

    async def test_a_corrupt_settings_row_reads_as_defaults(self):
        service = _service(stored="{not json at all")
        self.assertEqual(
            2, (await service.get_config()).limit_for(EntitlementState.FREE, A.LESSON_START).limit
        )


if __name__ == "__main__":
    unittest.main()
