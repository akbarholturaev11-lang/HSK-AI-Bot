# Release feedback draft — Google va Apple bilan kirish

Status: draft only. Do not send until an admin approves the release.

**Do not send this at all until the OAuth credentials are configured in the
deployment.** Until `GOOGLE_OAUTH_ENABLED` / `APPLE_OAUTH_ENABLED` and the
client ids are set, the buttons are hidden and users would be told about a
feature they cannot see.

## Release name

Google va Apple bilan kirish — bitta akkaunt, uchta yo‘l

## User message

Endi HSK AI ga Telegram, Google yoki Apple orqali kirish mumkin. Akkaunt,
obuna va progress — hammasi **o‘sha-o‘sha**: yangi usul qo‘shilganda ham
darslaringiz, XP va obunangiz joyida qoladi. Profil → “Kirish usullari”
bo‘limidan Google yoki Apple akkauntingizni ulab qo‘ying, keyin telefoningizni
almashtirsangiz ham bir bosishda kirasiz.

## Try it

Android: Profil → Sozlamalar → **Kirish usullari** → “Google ni ulash”.
Keyin ilovadan chiqib, login ekranida “Google bilan davom etish”ni sinab
ko‘ring.

Kompyuter (Mac/Windows): kirish ekranida Telegram tugmasining ostidagi
“Google bilan davom etish”.

## Feedback and reward

1–5 baho bering. Fikr bildirgan har bir foydalanuvchiga keyingi obuna uchun
10% chegirma beriladi; chegirma shartlari va amal qilish muddati yuborishdan
oldin admin tomonidan tasdiqlanadi.

Reward text shown BEFORE the rating is collected, not after.

## Confirmation after reward

Rahmat! Chegirmangiz akkauntingizga yozildi va keyingi to‘lovda avtomatik
qo‘llanadi.

## Target

Android va desktop ilovasidan foydalanadigan, akkaunti allaqachon Telegram
orqali ochilgan faol foydalanuvchilar.

**Explicitly NOT targeted:** users with no linked device, and anyone who has
never signed in. In this phase a provider login cannot create an account, so
they would hit “avval Telegram orqali kiring” and the message would read as
broken.

## Metrics

- Provider button impression → sign-in started → `oauth/assert` or callback
  success → `link/status` linked.
- `oauth_telegram_account_required` rate — if this is high, users are trying to
  sign in with a provider before linking it, and the copy needs work.
- Identity link success rate from Profile, and unlink rate.
- `oauth_identity_bound_to_other_user` rate — should be near zero; a spike means
  people are sharing provider accounts.
- Sign-in failures by stable code (`oauth_token_invalid`, `oauth_nonce_mismatch`,
  `oidc_jwks_unavailable`), watched separately from cancellations, which are a
  user choice and not a failure.
- Android: Credential Manager unavailable rate (no Google account / old Play
  Services) — decides whether the button is worth showing on older devices.

## Rules

- Do not auto-send. Ask the admin after deploy and send only on approval.
- Use the existing Telegram admin `Release feedback` module.
