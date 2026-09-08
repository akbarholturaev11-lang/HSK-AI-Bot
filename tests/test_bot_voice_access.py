"""Bot ovozidan kim foydalana oladi.

Bu yerda haqiqiy bug tuzatildi. Tekshiruv shunday edi:

    user.status == "active" and user.payment_status == "approved"

`end_date` ga UMUMAN qaralmasdi. Obuna tugaganda `payment_status` tasdiqlangan
holicha qoladi va faqat `end_date` o'tadi — ya'ni bir marta to'lagan odam bot
ovozini abadiy saqlab qolardi. Hech qanday xato yozilmasdi.

Ustiga: vaqtinchalik kirishi bor odam (referral mukofoti, otziv bonusi) ovozni
OLMASDI, holbuki Mini App unga kontentni ochardi.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.bot.handlers.messages import _can_use_voice


def _user(**overrides) -> SimpleNamespace:
    values = {"status": "free", "payment_status": "none", "end_date": None}
    values.update(overrides)
    return SimpleNamespace(**values)


class BotVoiceAccessTests(unittest.TestCase):
    def test_an_active_subscriber_may_use_voice(self):
        user = _user(
            status="active",
            payment_status="approved",
            end_date=datetime.now(timezone.utc) + timedelta(days=10),
        )
        self.assertTrue(_can_use_voice(user))

    def test_an_expired_subscription_no_longer_keeps_voice_forever(self):
        """Aynan tuzatilgan bug.

        `payment_status` "approved" holicha qoladi; faqat `end_date` o'tadi.
        Eski tekshiruv shu odamga ovozni abadiy ochiq qoldirardi.
        """
        expired = _user(
            status="active",
            payment_status="approved",
            end_date=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        self.assertFalse(_can_use_voice(expired))

    def test_an_approved_payment_without_an_end_date_is_not_enough(self):
        self.assertFalse(
            _can_use_voice(_user(status="active", payment_status="approved"))
        )

    def test_a_temporary_access_user_now_gets_voice_too(self):
        # Referral mukofoti va otziv bonusi shu shaklni qoldiradi. Mini App
        # unga kontentni ochardi; bot ovozi esa yopiq edi.
        bonus = _user(
            status="active", end_date=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        self.assertTrue(_can_use_voice(bonus))

    def test_a_free_user_does_not_get_voice(self):
        self.assertFalse(_can_use_voice(_user()))

    def test_a_blocked_user_does_not_get_voice(self):
        self.assertFalse(
            _can_use_voice(
                _user(
                    status="blocked",
                    payment_status="approved",
                    end_date=datetime.now(timezone.utc) + timedelta(days=10),
                )
            )
        )

    def test_a_missing_user_is_refused_rather_than_raising(self):
        self.assertFalse(_can_use_voice(None))


if __name__ == "__main__":
    unittest.main()
