"""Private, bounded Cloudflare R2 mirror for 24h Admin PWA aggregate snapshots.

Only server-authenticated aggregate JSON travels through this adapter. Bucket
permissions must be private; never expose R2 object links, signed client URLs,
secrets or raw PII. Snapshot freshness/schema validation belongs to the reader.
"""
import asyncio
import re

MAX_OBJECT_BYTES = 128 * 1024


class R2ConfigurationError(RuntimeError):
    pass


class R2Unavailable(RuntimeError):
    pass


class PrivateR2AggregateStore:
    def __init__(self, *, settings_obj, client=None):
        self.settings = settings_obj
        self.enabled = bool(getattr(settings_obj, "ADMIN_PWA_R2_AGGREGATE_ENABLED", False))
        self._client = client
        if self.enabled:
            account = getattr(settings_obj, "ADMIN_PWA_R2_ACCOUNT_ID", "")
            bucket = getattr(settings_obj, "ADMIN_PWA_R2_BUCKET", "")
            access = getattr(settings_obj, "ADMIN_PWA_R2_ACCESS_KEY_ID", "")
            secret = getattr(settings_obj, "ADMIN_PWA_R2_SECRET_ACCESS_KEY", "")
            if (not re.fullmatch(r"[0-9a-f]{32}", account or "")
                    or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket or "")
                    or not access or not secret):
                raise R2ConfigurationError("Private aggregate R2 bucket credentials unavailable")
            self._bucket = bucket
            self._account = account

    def _get_client(self):
        if self._client is None:
            # Boto3 imports only on an explicitly enabled, configured path.
            from boto3.session import Session
            from botocore.config import Config
            self._client = Session().client(
                "s3", endpoint_url=f"https://{self._account}.r2.cloudflarestorage.com",
                region_name="auto",
                aws_access_key_id=self.settings.ADMIN_PWA_R2_ACCESS_KEY_ID,
                aws_secret_access_key=self.settings.ADMIN_PWA_R2_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4", connect_timeout=1,
                              read_timeout=2, retries={"max_attempts": 0},
                              max_pool_connections=3),
            )
        return self._client

    @staticmethod
    def _key(kind, namespace, variant):
        if (kind not in ("statistics", "feedback")
                or not re.fullmatch(r"[0-9a-f]{24}", namespace)
                or not re.fullmatch(r"[a-z0-9_-]{1,32}", variant)):
            raise ValueError("Invalid private aggregate key")
        return f"admin-pwa/aggregates/v1/{namespace}/{kind}/{variant}.json"

    async def get(self, *, kind, namespace, variant):
        if not self.enabled:
            return None
        key = self._key(kind, namespace, variant)

        def read():
            response = self._get_client().get_object(Bucket=self._bucket, Key=key)
            body = response["Body"]
            try:
                if response.get("ContentLength", MAX_OBJECT_BYTES + 1) > MAX_OBJECT_BYTES:
                    return None
                raw = body.read(MAX_OBJECT_BYTES + 1)
                return raw if isinstance(raw, bytes) and 0 < len(raw) <= MAX_OBJECT_BYTES else None
            finally:
                body.close()

        try:
            return await asyncio.wait_for(asyncio.to_thread(read), timeout=3)
        except Exception as exc:
            # R2 may return NoSuchKey; cache absence is not a server error.
            if getattr(getattr(exc, "response", {}), "get", lambda *_: {})("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return None
            raise R2Unavailable("Private R2 aggregate read unavailable") from None

    async def put(self, *, kind, namespace, variant, raw):
        if not self.enabled:
            return
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_OBJECT_BYTES:
            raise ValueError("Aggregate R2 payload exceeds allowed size")
        key = self._key(kind, namespace, variant)

        def write():
            self._get_client().put_object(
                Bucket=self._bucket, Key=key, Body=raw, ContentType="application/json",
                CacheControl="private, no-store",
                Metadata={"schema": "admin-pwa-aggregates-v1"},
            )
        try:
            await asyncio.wait_for(asyncio.to_thread(write), timeout=3)
        except Exception:
            raise R2Unavailable("Private R2 aggregate write unavailable") from None
