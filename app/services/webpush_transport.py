"""Shared RFC 8291/8292 Web Push HTTP transport; callers own identity and policy."""
import asyncio


async def send_webpush(subscription, data, private_key, subject, *, ttl=180, timeout=8):
    """Send one already-authorized visible Web Push outside the event loop."""
    from py_vapid import Vapid
    from pywebpush import webpush

    def send():
        result = webpush(
            subscription_info=subscription,
            data=data,
            vapid_private_key=Vapid.from_raw(private_key.encode("ascii")),
            vapid_claims={"sub": subject},
            content_encoding="aes128gcm",
            ttl=ttl,
            timeout=timeout,
            verbose=False,
        )
        return int(result.status_code)

    return await asyncio.wait_for(asyncio.to_thread(send), timeout=timeout + 4)
