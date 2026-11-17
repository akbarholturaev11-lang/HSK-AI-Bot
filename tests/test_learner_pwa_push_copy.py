"""Event presentation regressions: actual Telegram sources, no transport mocks of copy."""
import json
from types import SimpleNamespace as Row
import unittest
from unittest.mock import AsyncMock, patch

from app.bot.utils.i18n import t
from app.services.learner_pwa_push_copy import (
    account_push_copy, course_push_copy, fallback_copy, payment_push_copy, plain_text, push_copy,
)
from app.services.notification_template_service import TEMPLATE_KEYS, default_text


LANGUAGES = ('uz', 'ru', 'tj')


def course_row(**fields):
    values = dict(key='daily_goal', language='uz', title='Old title', body='Old body',
                  source='motivation_reminder', params=None, dedupe_key=None)
    values.update(fields)
    return Row(**values)


class LearnerPwaPushCopyTests(unittest.IsolatedAsyncioTestCase):
    def test_html_entities_breaks_emoji_and_brand_are_adapted_once(self):
        text = '<b>🔥 Salom &amp; xush kelibsiz!</b><br>HSK AI Pro ochildi.<p>学习 &lt;3</p>'
        self.assertEqual(push_copy(text, title='Fallback', body='Fallback'),
                         ('🔥 Salom & xush kelibsiz!', 'Pro ochildi.\n学习 <3'))
        self.assertEqual(push_copy('<b>🥇 &lt;Alice&gt;</b>\nXP &lt; 20', title='', body=''),
                         ('🥇 <Alice>', 'XP < 20'))
        self.assertEqual(plain_text('HSK AI'), '')
        self.assertEqual(plain_text('HSK AI’ni oching'), 'oching')

    def test_long_cjk_and_emoji_copy_fits_one_web_push_without_losing_tail_silently(self):
        title, body = push_copy('🔥 Title\n' + '📚学习' * 2000, title='', body='')
        encoded = json.dumps(dict(title=title, body=body, lang='tj',
                                 tag='hsk-' + 'a'*24, url='/iphone-pwa/course?notice=1'), ensure_ascii=False)
        self.assertLess(len(encoded.encode()), 3000)
        self.assertTrue(body.endswith('…'))
        self.assertNotIn('\ufffd', body)

    async def test_all_six_reminder_types_keep_actual_telegram_headline_body_and_emoji(self):
        fields = dict(name='Ali &amp; 王', league='Jade', rank=4, xp_gap=23,
                      lesson=7, minutes=15, streak=8)
        for language in LANGUAGES:
            for key in TEMPLATE_KEYS:
                original = default_text(key, language).format(**fields)
                row = course_row(key=key, language='old', params={'template_service': key, **fields})
                with patch('app.services.learner_pwa_push_copy.NotificationTemplateService.resolve',
                           new=AsyncMock(return_value={'text': default_text(key, language)})):
                    title, body = await course_push_copy(None, row, language)
                self.assertEqual(title + '\n' + body, plain_text(original))
                self.assertNotIn('HSK AI', title + body)
                self.assertNotIn('{', title + body)

    async def test_custom_admin_template_is_resolved_in_current_selected_language(self):
        row = course_row(params={'template_service': 'daily_goal', 'minutes': 12})
        with patch('app.services.learner_pwa_push_copy.NotificationTemplateService.resolve',
                   new=AsyncMock(return_value={'text': '🎯 Мақсади шумо\nҲамагӣ {minutes} дақиқа!'})) as resolve:
            self.assertEqual(await course_push_copy(None, row, 'tj'),
                             ('🎯 Мақсади шумо', 'Ҳамагӣ 12 дақиқа!'))
            resolve.assert_awaited_once_with('daily_goal', 'tj')
        self.assertEqual(row.language, 'uz')  # presentation must never rewrite source metadata

    async def test_legacy_trial_slots_keep_distinct_48h_and_final_day_copy_in_every_language(self):
        for language in LANGUAGES:
            for slot in (0, 2):
                row = course_row(key='trial_expiring', source='trial_reminder',
                                 dedupe_key=f'trial_reminder:2026-11-13:{slot}')
                title, body = await course_push_copy(None, row, language)
                expected = t('trial_expiring_soon', language, days=2) if slot else t('trial_expired_notice', language)
                self.assertEqual(title+'\n'+body, plain_text(expected))

    async def test_fixed_course_templates_relocalize_remaining_reset_time_and_lesson_summary(self):
        cases = [
            ('limit_lesson_warning', 'limit_lesson_warning_notice', {'remaining': 3}),
            ('limit_lesson_spent', 'limit_lesson_spent_notice', {}),
            ('limit_daily_spent', 'limit_daily_spent_notice', {'reset_time': '06:20'}),
            ('limit_daily_spent', 'limit_daily_spent_notice_no_time', {}),
            ('lesson_time', 'course_reminder_text', {'vocab': 8, 'dialogues': 2}),
        ]
        for language in LANGUAGES:
            for key, template, fields in cases:
                row = course_row(key=key, params={'template': template, **fields})
                title, body = await course_push_copy(None, row, language)
                self.assertEqual(title+'\n'+body, plain_text(t(template, language, **fields)))

    async def test_old_rows_do_not_send_stale_foreign_language_or_unresolved_parameters(self):
        for language in ('ru', 'tj'):
            row = course_row()
            self.assertEqual(await course_push_copy(None, row, language), fallback_copy(row.key, language))
        for language in LANGUAGES:
            titles = []
            for key in (*TEMPLATE_KEYS, 'lesson_time', 'limit_lesson_warning', 'limit_lesson_spent',
                        'limit_daily_spent', 'subscription_expiring', 'subscription_offer', 'trial_expiring'):
                title, body = fallback_copy(key, language)
                self.assertTrue(title and body)
                self.assertNotIn('HSK AI', title+body)
                titles.append(title)
            self.assertEqual(len(set(titles)), len(titles))

    def test_account_sources_and_fix_receipts_keep_their_own_purpose(self):
        for language in LANGUAGES:
            for key, template in [('daily_limit_renewed', 'daily_limit_renewed'),
                                  ('subscription_expiring', 'subscription_expires_tomorrow')]:
                row = course_row(key=key, reason='', telegram_payload=None)
                title, body = account_push_copy(row, language)
                self.assertIn(plain_text(t(template, language)), title+'\n'+body)
                self.assertNotIn('HSK AI', title+body)
            blocked = course_row(key='pwa_account_restriction', reason='', telegram_payload=None)
            self.assertEqual(account_push_copy(blocked, language), fallback_copy(blocked.key, language))
            for reason in ('android_fix_1_1', 'android_update_1_1'):
                fixed = course_row(reason=reason)
                title, body = account_push_copy(fixed, language)
                self.assertIn('✅', title)
                self.assertIn('🔥', body)

    def test_discount_custom_phone_body_and_headline_keep_precedence_without_app_name(self):
        row = course_row(key='discount_offer', reason='discount_notification', title='HSK AI',
                         body='🎁 <b>Maxsus taklif</b>\nSiz uchun 20% chegirma.',
                         telegram_payload={'text': '🎁 Maxsus taklif\nSiz uchun 20% chegirma.\nMini App'})
        self.assertEqual(account_push_copy(row, 'uz'), ('🎁 Maxsus taklif', 'Siz uchun 20% chegirma.'))
        self.assertEqual(account_push_copy(row, 'tj'), fallback_copy('discount_offer', 'tj'))

    async def test_limit_prefix_keeps_original_state_and_quota_in_current_language(self):
        from app.services.entitlements.decision import limit_text
        context = dict(action='ai.question', state='TRIAL_ACTIVE', limit=5, remaining=0, window='daily')
        row = course_row(key='limit_daily_spent', params={
            'template': 'limit_daily_spent_notice', 'reset_time': '06:20', 'limit_context': context})
        for language in LANGUAGES:
            title, body = await course_push_copy(None, row, language)
            expected = plain_text(limit_text(**context, language=language) + '\n\n' +
                                  t('limit_daily_spent_notice', language, reset_time='06:20'))
            self.assertEqual(title+'\n'+body, expected)

    def test_account_trial_slots_relocalize_from_the_original_telegram_template(self):
        for language in LANGUAGES:
            for template, fields in [('trial_expiring_soon', {'days': 2}), ('trial_expired_notice', {})]:
                row = course_row(key='trial_expiring', reason='trial_reminder',
                                 telegram_payload={'text': t(template, 'uz', **fields)})
                title, body = account_push_copy(row, language)
                self.assertEqual(title+'\n'+body, plain_text(t(template, language, **fields)))

    def test_discount_phone_body_keeps_campaign_title_under_telegram_emoji_headline(self):
        row = course_row(key='discount_offer', reason='discount_notification',
                         title='🎁 Maxsus chegirma tayyor', body='Bahorgi taklif\nChegirma: 20%',
                         telegram_payload={'text': '🎁 <b>Maxsus chegirma tayyor</b>\nBahorgi taklif\nChegirma: 20%\nMini App'})
        self.assertEqual(account_push_copy(row, 'uz'),
                         ('🎁 Maxsus chegirma tayyor', 'Bahorgi taklif\nChegirma: 20%'))

    async def test_localized_lesson_label_does_not_keep_old_language_in_template_fields(self):
        row = course_row(key='lesson_unfinished', level='hsk1', lesson_order=4,
                         params={'template_service': 'lesson_unfinished', 'lesson': 'HSK1 4-dars', 'minutes': 15})
        with patch('app.services.learner_pwa_push_copy.NotificationTemplateService.resolve',
                   new=AsyncMock(return_value={'text': default_text('lesson_unfinished', 'ru')})):
            title, body = await course_push_copy(None, row, 'ru')
        self.assertIn('HSK1 урок 4', title)
        self.assertNotIn('dars', title+body)

    async def test_invalid_template_does_not_leak_placeholders(self):
        row = course_row(params={'template': 'limit_lesson_warning_notice'})
        title, body = await course_push_copy(None, row, 'tj')
        self.assertNotIn('{', title+body)

    def test_payment_decisions_reuse_telegram_copy_and_distinguish_course_unlock(self):
        for language in LANGUAGES:
            for status in ('approved', 'rejected'):
                payment = Row(payment_status=status, plan_type='1_month', admin_comment='PRIVATE', amount=149)
                title, body = payment_push_copy(payment, language)
                expected = plain_text(t('user_payment_'+status, language))
                self.assertEqual(title+'\n'+body, expected)
                self.assertNotIn('HSK AI', title+body)
                self.assertNotIn('PRIVATE', title+body)
                self.assertNotIn('149', title+body)
                payment.plan_type = 'hsk30_unlock'
                unlock_title, unlock_body = payment_push_copy(payment, language)
                self.assertNotEqual((title, body), (unlock_title, unlock_body))
