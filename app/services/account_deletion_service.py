"""Deletion-only proof: never create/link accounts or issue login credentials."""

from datetime import datetime, timedelta, timezone
import hmac
import secrets
import uuid

from sqlalchemy import delete, func, select, text

from app.db.models.account_deletion import AccountDeletionRequest
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.repositories.user_repo import UserRepository
from app.services import apple_auth, google_auth
from app.services.desktop_auth_service import DesktopAuthError, DesktopAuthService
from app.services.native_oauth_service import NativeOAuthService, redirect_base_url
from app.services.oidc_verifier import OidcVerificationError

TTL_SECONDS = 600
PROCESSING_DAYS = 30
STATE_PREFIX = "delete."
BROWSER_COOKIE = "hsk_deletion_browser"


def now():
    return datetime.now(timezone.utc)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class AccountDeletionError(DesktopAuthError):
    pass


class AccountDeletionService:
    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj
        self.auth = DesktopAuthService(session, settings_obj)

    def _hash(self, purpose, value):
        return self.auth._hash("account-deletion-" + purpose, str(value))

    def providers(self):
        providers = ["telegram"] if getattr(self.settings, "BOT_USERNAME", "") else []
        if redirect_base_url(self.settings):
            if google_auth.is_configured(self.settings, platform="windows"):
                providers.append("google")
            if apple_auth.is_configured(self.settings):
                providers.append("apple")
        return providers

    async def _admit(self, client):
        # A shared PostgreSQL lock enforces limits across workers, not in memory.
        if self.session.get_bind().dialect.name == "postgresql":
            await self.session.execute(text("SELECT pg_advisory_xact_lock(736840103)"))
        cutoff = now() - timedelta(seconds=TTL_SECONDS)
        client_hash = self._hash("client", client)
        total = await self.session.scalar(select(func.count()).select_from(AccountDeletionRequest).where(
            AccountDeletionRequest.created_at >= cutoff))
        own = await self.session.scalar(select(func.count()).select_from(AccountDeletionRequest).where(
            AccountDeletionRequest.created_at >= cutoff, AccountDeletionRequest.client_hash == client_hash))
        if total >= 120 or own >= 12:
            raise AccountDeletionError("deletion_rate_limited", status_code=429)
        return client_hash

    async def start(self, *, provider, client, browser=None, user=None):
        if user is None and provider not in self.providers():
            raise AccountDeletionError("deletion_provider_unavailable", status_code=503)
        client_hash = await self._admit(client)
        secret = secrets.token_urlsafe(32)
        created = now()
        row = AccountDeletionRequest(
            id=str(uuid.uuid4()), provider=provider, status="verified" if user else "pending",
            user_id=user.id if user else None, secret_hash=self._hash("secret", secret),
            browser_hash=self._hash("browser", browser) if browser else None,
            client_hash=client_hash, created_at=created,
            expires_at=created + timedelta(seconds=TTL_SECONDS), verified_at=created if user else None,
        )
        self.session.add(row)
        await self.session.flush()
        result = self._result(row, user=user)
        result["secret"] = secret
        if not user and provider == "telegram":
            username = str(self.settings.BOT_USERNAME).lstrip("@")
            result["bot_deep_link"] = f"https://t.me/{username}?start=delete_{row.id.replace('-', '')}"
        elif not user:
            oauth = NativeOAuthService(self.session, self.settings)
            builder = google_auth.authorize_url if provider == "google" else apple_auth.authorize_url
            result["authorize_url"] = builder(
                settings_obj=self.settings, redirect_uri=oauth.redirect_uri(provider),
                state=self.state(row.id), nonce=self._hash("nonce", row.id),
                code_challenge=oauth.code_challenge(self._hash("pkce", row.id)),
            )
        await self.session.commit()
        return result

    def state(self, request_id):
        return f"{STATE_PREFIX}{request_id}.{self._hash('state', request_id)}"

    async def _row(self, request_id, *, retry=False):
        # Lock the account BEFORE its receipts. This also matches legacy admin
        # purge ordering and prevents duplicate receipts from deadlocking when
        # processed concurrently. Re-read after the lock: another transaction
        # may already have completed/purged the account while we were waiting.
        candidate = await self.session.scalar(select(AccountDeletionRequest).where(
            AccountDeletionRequest.id == request_id))
        candidate_user_id = candidate.user_id if candidate else None
        if candidate_user_id:
            await self.session.execute(select(User.id).where(
                User.id == candidate_user_id).with_for_update())
        row = await self.session.scalar(select(AccountDeletionRequest).where(
            AccountDeletionRequest.id == request_id).with_for_update().execution_options(populate_existing=True))
        if row is None:
            raise AccountDeletionError("deletion_invalid", status_code=404)
        if row.user_id and row.user_id != candidate_user_id:
            # Verification can bind a formerly pending receipt while we wait
            # for its row lock. Release that lock and restart in account-first
            # order rather than taking a new account lock behind the receipt.
            await self.session.rollback()
            if retry:
                raise AccountDeletionError("deletion_busy", status_code=409)
            return await self._row(request_id, retry=True)
        if row.status in {"pending", "verified"} and utc(row.expires_at) <= now():
            raise AccountDeletionError("deletion_expired", status_code=410)
        return row

    def _browser(self, row, browser):
        if row.browser_hash and not hmac.compare_digest(row.browser_hash, self._hash("browser", browser or "")):
            raise AccountDeletionError("deletion_browser_mismatch", status_code=403)

    async def _owned(self, request_id, secret, browser):
        row = await self._row(request_id)
        if not hmac.compare_digest(row.secret_hash, self._hash("secret", secret)):
            raise AccountDeletionError("deletion_invalid", status_code=403)
        self._browser(row, browser)
        return row

    def _result(self, row, *, user=None):
        result = {"ok": True, "request_id": row.id, "status": row.status,
                  "expires_in": max(0, int((utc(row.expires_at) - now()).total_seconds()))}
        if user and row.status == "verified":
            result["account_label"] = user.full_name or "HSK AI account"
        for field in ("requested_at", "due_at", "completed_at"):
            if getattr(row, field):
                result[field] = utc(getattr(row, field)).isoformat()
        return result

    async def status(self, *, request_id, secret, browser=None):
        row = await self._owned(request_id, secret, browser)
        user = await self.session.get(User, row.user_id) if row.user_id else None
        return self._result(row, user=user)

    async def complete_oauth(self, *, provider, state, code, browser):
        # Namespaced state can never be used by the ordinary sign-in callback.
        parts = str(state).split(".")
        if len(parts) != 3 or parts[0] != "delete" or not hmac.compare_digest(
            str(state), self.state(parts[1])
        ):
            raise AccountDeletionError("deletion_invalid", status_code=400)
        row = await self._row(parts[1])
        self._browser(row, browser)
        if row.provider != provider or provider not in {"google", "apple"} or row.status != "pending":
            raise AccountDeletionError("deletion_invalid", status_code=409)
        oauth = NativeOAuthService(self.session, self.settings)
        adapter = google_auth if provider == "google" else apple_auth
        try:
            token = await adapter.exchange_code(
                code, settings_obj=self.settings, redirect_uri=oauth.redirect_uri(provider),
                code_verifier=self._hash("pkce", row.id),
                timeout_seconds=float(getattr(self.settings, "OAUTH_HTTP_TIMEOUT_SECONDS", 8)),
            )
            verifier = google_auth.verify_desktop_id_token if provider == "google" else apple_auth.verify_id_token_for_service
            verified = await verifier(token, settings_obj=self.settings,
                nonce=self._hash("nonce", row.id),
                max_age_seconds=int(getattr(self.settings, "OAUTH_ID_TOKEN_MAX_AGE_SECONDS", 300)))
            identity = await self.session.scalar(select(UserIdentity).where(
                UserIdentity.provider == provider,
                UserIdentity.subject_hash == self.auth.identity_subject_hash(provider, verified.subject)))
            user = await self.session.get(User, identity.user_id) if identity else None
            if user is None:
                raise AccountDeletionError("deletion_account_not_found", status_code=404)
        except (OidcVerificationError, AccountDeletionError):
            row.status = "failed"
            await self.session.commit()
            raise
        # Blocked learners retain their deletion rights; no access is granted.
        row.user_id = user.id
        row.status = "verified"
        row.verified_at = now()
        await self.session.commit()
        return self._result(row, user=user)

    async def verify_telegram(self, *, request_id, telegram_id):
        row = await self._row(request_id)
        if row.provider != "telegram" or row.status != "pending":
            raise AccountDeletionError("deletion_invalid", status_code=409)
        user = await self.session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            raise AccountDeletionError("deletion_account_not_found", status_code=404)
        row.user_id = user.id
        row.status = "verified"
        row.verified_at = now()
        await self.session.commit()
        return self._result(row, user=user)

    async def confirm(self, *, request_id, secret, browser=None):
        row = await self._owned(request_id, secret, browser)
        if row.status in {"submitted", "completed"}:
            return self._result(row)
        if row.status != "verified" or not row.user_id:
            raise AccountDeletionError("deletion_verification_required", status_code=409)
        user = await self.session.scalar(select(User).where(User.id == row.user_id).with_for_update())
        if user is None:
            raise AccountDeletionError("deletion_account_not_found", status_code=404)
        existing = await self.session.scalar(select(AccountDeletionRequest).where(
            AccountDeletionRequest.active_user_id == user.id))
        if existing:
            # Duplicate confirmations receive their own usable receipt, but
            # only the original active row is placed in the operator queue.
            row.requested_at, row.due_at = existing.requested_at, existing.due_at
        else:
            row.requested_at = now()
            row.due_at = row.requested_at + timedelta(days=PROCESSING_DAYS)
            row.active_user_id = user.id
        row.status = "submitted"
        await self.session.commit()
        return self._result(row)

    async def submit_telegram(self, telegram_id):
        user = await self.session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            raise AccountDeletionError("deletion_account_not_found", status_code=404)
        prepared = await self.start(provider="telegram", client=f"telegram:{telegram_id}", user=user)
        return await self.confirm(request_id=prepared["request_id"], secret=prepared["secret"])

    async def process(self, *, request_id, expected_user_id):
        row = await self._row(request_id)
        if row.status == "completed":
            return self._result(row)
        if row.status != "submitted" or row.user_id != expected_user_id:
            raise AccountDeletionError("deletion_invalid", status_code=409)
        user = await self.session.get(User, expected_user_id)
        if not user or user.telegram_id in getattr(self.settings, "admin_id_list", []):
            raise AccountDeletionError("cannot_delete_admin", status_code=403)
        # Keep only an anonymous receipt. Proofs and account-bound challenges
        # are purged in the same transaction as the established account purge.
        await self.session.execute(delete(AccountDeletionRequest).where(
            AccountDeletionRequest.user_id == user.id,
            AccountDeletionRequest.status != "submitted"))
        receipts = (await self.session.scalars(select(AccountDeletionRequest).where(
            AccountDeletionRequest.user_id == user.id,
            AccountDeletionRequest.status == "submitted"))).all()
        for receipt in receipts:
            receipt.user_id = receipt.active_user_id = None
            receipt.client_hash = self._hash("anonymous", receipt.id)
            receipt.status, receipt.completed_at = "completed", now()
        await self.session.flush()
        if not await UserRepository(self.session).delete_by_user_id(user.id):
            raise AccountDeletionError("deletion_account_not_found", status_code=404)
        await self.session.commit()
        if user.telegram_id:
            from app.services.blocked_user_guard import invalidate
            invalidate(user.telegram_id)
        return self._result(row)

    async def cleanup(self):
        # Legacy admin deletion uses the same purge but not this service. Its
        # SET NULL foreign keys prove the account is gone; reconcile receipts
        # so they cannot remain "submitted" forever outside the operator queue.
        orphans = (await self.session.scalars(select(AccountDeletionRequest).where(
            AccountDeletionRequest.status == "submitted",
            AccountDeletionRequest.user_id.is_(None)))).all()
        for receipt in orphans:
            receipt.status, receipt.completed_at = "completed", now()
            receipt.active_user_id = None
            receipt.client_hash = self._hash("anonymous", receipt.id)
        await self.session.execute(delete(AccountDeletionRequest).where(
            AccountDeletionRequest.status == "verified", AccountDeletionRequest.user_id.is_(None)))
        # Submitted requests, including overdue ones, must NEVER expire away.
        await self.session.execute(delete(AccountDeletionRequest).where(
            AccountDeletionRequest.status.notin_(["submitted"]),
            AccountDeletionRequest.created_at < now() - timedelta(days=30),
            (AccountDeletionRequest.completed_at.is_(None) |
             (AccountDeletionRequest.completed_at < now() - timedelta(days=30))))
            .execution_options(synchronize_session="fetch"))
        await self.session.commit()
