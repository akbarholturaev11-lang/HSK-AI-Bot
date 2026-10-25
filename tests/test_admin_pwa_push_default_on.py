"""Owner-only Apple PWA push auto-enrollment regression guards (no APNs traffic)."""
from pathlib import Path

from app.config import Settings
from app.services.admin_pwa_push_dispatch import sender_config


ROOT = Path(__file__).resolve().parents[1]


def test_owner_push_is_default_on_but_never_sends_without_valid_secrets():
    settings = Settings.model_construct(
        ADMIN_PWA_ENABLED=True, ADMIN_PWA_PUBLIC_ORIGIN="https://hskai.app",
    )
    assert settings.ADMIN_PWA_PUSH_ENABLED is True
    assert settings.ADMIN_PWA_PUSH_SEND_ENABLED is True
    # Never generate ephemeral VAPID/storage keys, send from an unconfigured
    # installation, or silently downgrade encryption to get "default on".
    assert sender_config(settings) is None
    settings.ADMIN_PWA_PUSH_SEND_ENABLED = False
    assert sender_config(settings) is None


def test_apple_permission_requires_a_click_but_existing_grants_restore_on_login():
    source = (ROOT / "app/static/admin-pwa/app.js").read_text()
    assert "void restorePushAfterLogin().catch(()=>{});" in source
    restore = source.split("async function restorePushAfterLogin(){", 1)[1].split(
        "async function pushSettings(){", 1
    )[0]
    assert "Notification.permission==='granted'" in restore
    assert "await registerPushSubscription(subscription,platform)" in restore
    assert "Notification.requestPermission(" not in restore
    assert "updatePushQuickButton();" in restore
    click = source.split("async function enablePush(){", 1)[1].split(
        "async function revokePush(", 1
    )[0]
    assert click.index("registration.pushManager.subscribe({") < click.index(
        "await subscriptionPromise"
    )
    assert "await registerPushSubscription(subscription,applePushPlatform());" in click
