import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.bot.handlers.admin_payments import (
    admin_payment_approve_handler,
    admin_payment_reject_handler,
)
from app.services.hsk30_unlock_service import HSK30_UNLOCK_PLAN_TYPE


def _callback(data: str):
    return SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=999),
        answer=AsyncMock(),
        message=SimpleNamespace(edit_reply_markup=AsyncMock()),
        bot=SimpleNamespace(delete_message=AsyncMock()),
    )


class Hsk30AdminPaymentFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_approval_grants_only_permanent_unlock(self):
        callback = _callback("admin_payment:approve:44")
        session = SimpleNamespace(
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )
        payment = SimpleNamespace(
            id=44,
            user_telegram_id=700,
            plan_type=HSK30_UNLOCK_PLAN_TYPE,
            payment_method="visa",
            payment_status="pending",
            discount_source="none",
            checkout_msg_id=None,
            screenshot_msg_id=None,
            waiting_msg_id=None,
        )
        user = SimpleNamespace(id=7, telegram_id=700)

        with (
            patch("app.bot.handlers.admin_payments._is_admin", return_value=True),
            patch("app.bot.handlers.admin_payments.PaymentRepository") as payment_repo_cls,
            patch("app.bot.handlers.admin_payments.UserRepository") as user_repo_cls,
            patch("app.bot.handlers.admin_payments.SubscriptionService") as subscription_cls,
            patch("app.bot.handlers.admin_payments.PaymentNotifyService") as notify_cls,
            patch("app.bot.handlers.admin_payments.PartnerService") as partner_cls,
            patch("app.bot.handlers.admin_payments.Hsk30UnlockService") as unlock_cls,
            patch("app.bot.handlers.admin_payments.ConversionFunnelService") as funnel_cls,
            patch("app.bot.handlers.admin_payments.CourseMiniAppAnalyticsService") as analytics_cls,
        ):
            payment_repo = payment_repo_cls.return_value
            payment_repo.get_by_id = AsyncMock(return_value=payment)

            async def approve(row, **kwargs):
                row.payment_status = "approved"
                return True

            payment_repo.approve = AsyncMock(side_effect=approve)
            user_repo_cls.return_value.get_by_telegram_id = AsyncMock(return_value=user)
            unlock_cls.return_value.grant = AsyncMock(return_value=True)
            funnel_cls.return_value.record = AsyncMock()
            analytics_cls.return_value.record_server_event = AsyncMock(
                return_value={"recorded": False}
            )
            notify_cls.return_value.notify_hsk30_unlock_approved = AsyncMock()
            notify_cls.return_value.notify_payment_approved = AsyncMock()
            subscription_cls.return_value.activate_plan = AsyncMock()
            partner_cls.return_value.record_approved_payment = AsyncMock()
            partner_cls.return_value.notify_partner = AsyncMock()

            await admin_payment_approve_handler(callback, session)

            unlock_cls.return_value.grant.assert_awaited_once_with(
                user=user,
                payment=payment,
            )
            subscription_cls.return_value.activate_plan.assert_not_awaited()
            partner_cls.return_value.record_approved_payment.assert_not_awaited()
            partner_cls.return_value.notify_partner.assert_not_awaited()
            notify_cls.return_value.notify_hsk30_unlock_approved.assert_awaited_once()
            notify_cls.return_value.notify_payment_approved.assert_not_awaited()
            session.rollback.assert_not_awaited()
            callback.answer.assert_awaited_with(
                "✅ HSK 3.0 ochildi!",
                show_alert=True,
            )

    async def test_rejection_does_not_unlock_or_change_subscription_selection(self):
        callback = _callback("admin_payment:reject:45")
        session = SimpleNamespace(
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )
        payment = SimpleNamespace(
            id=45,
            user_telegram_id=701,
            plan_type=HSK30_UNLOCK_PLAN_TYPE,
            payment_method="visa",
            payment_status="pending",
        )
        user = SimpleNamespace(id=8, telegram_id=701)

        with (
            patch("app.bot.handlers.admin_payments._is_admin", return_value=True),
            patch("app.bot.handlers.admin_payments.PaymentRepository") as payment_repo_cls,
            patch("app.bot.handlers.admin_payments.UserRepository") as user_repo_cls,
            patch("app.bot.handlers.admin_payments.PaymentNotifyService") as notify_cls,
            patch("app.bot.handlers.admin_payments.Hsk30UnlockService") as unlock_cls,
            patch("app.bot.handlers.admin_payments.ConversionFunnelService") as funnel_cls,
        ):
            payment_repo = payment_repo_cls.return_value
            payment_repo.get_by_id = AsyncMock(return_value=payment)
            payment_repo.reject = AsyncMock(return_value=True)
            user_repo = user_repo_cls.return_value
            user_repo.get_by_telegram_id = AsyncMock(return_value=user)
            user_repo.set_selected_plan_type = AsyncMock()
            notify_cls.return_value.notify_hsk30_unlock_rejected = AsyncMock()
            notify_cls.return_value.notify_payment_rejected = AsyncMock()
            unlock_cls.return_value.grant = AsyncMock()
            funnel_cls.return_value.record = AsyncMock()

            await admin_payment_reject_handler(callback, session)

            unlock_cls.return_value.grant.assert_not_awaited()
            user_repo.set_selected_plan_type.assert_not_awaited()
            notify_cls.return_value.notify_hsk30_unlock_rejected.assert_awaited_once()
            notify_cls.return_value.notify_payment_rejected.assert_not_awaited()
            session.commit.assert_awaited_once()
            callback.answer.assert_awaited_with("❌ Rad etildi", show_alert=True)


if __name__ == "__main__":
    unittest.main()
