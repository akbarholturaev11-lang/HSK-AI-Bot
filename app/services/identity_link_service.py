"""Account resolution and linking for Google / Apple identities.

Every rule here exists to stop one specific takeover. Read the reasoning before
relaxing any of them.

**An identity belongs to exactly one internal user, forever.** A row is never
moved between users. If it could be moved, whoever controls the provider
account could hop it onto a paying subscriber and then sign in as them.

**Email is never used to find an account.** ``email_hash`` and
``email_display`` exist for support and abuse analytics only. An email address
is attacker-influenceable, provider-scoped and recyclable — Google Workspace
addresses are reassigned when a domain changes hands, Apple private-relay
addresses are per-app and revocable, and ``email_verified`` asserts only that
the *provider* checked it, never that the same human owns our account. Matching
on it is exactly what turns "sign in with Google" into subscription takeover.

**A bound device does not authorise a link.** A device already signed in as
user X proves the *device* is X's, not that the person authenticating right now
is X. Someone on a borrowed, signed-in laptop would otherwise attach their own
Google identity to the owner's paid account and keep access from anywhere.
Linking is only ever an explicit, bearer-authenticated action.

**A blocked account cannot sign in.** The Telegram flow gets this for free:
``BlockedUserMiddleware`` stops every bot handler, so a blocked user can never
reach the approval step and can never mint a new session. A provider flow has
no bot step, so the same door has to be closed explicitly here — otherwise
linking Google before being blocked would leave a way back in.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update

from app.db.models.desktop import DesktopDevice, DesktopSession
from app.db.models.user import User
from app.db.models.user_identity import UserIdentity
from app.services.desktop_auth_service import DesktopAuthService
from app.services.oidc_verifier import VerifiedIdentity
from app.services.user_access_state_service import (
    UserAccessState,
    UserAccessStateService,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IdentityLinkError(RuntimeError):
    def __init__(self, code: str, *, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def mask_email(email: str | None) -> str | None:
    """Show enough to recognise the account, not enough to harvest it."""

    value = str(email or "").strip()
    if "@" not in value:
        return None
    local, _, domain = value.partition("@")
    if len(local) <= 2:
        hidden = local[:1] + "*"
    else:
        hidden = f"{local[0]}{'*' * min(6, len(local) - 2)}{local[-1]}"
    return f"{hidden}@{domain}"


class IdentityLinkService:
    def __init__(self, session, settings_obj):
        self.session = session
        self.settings = settings_obj
        self._auth = DesktopAuthService(session, settings_obj)

    def subject_hash(self, provider: str, subject: str) -> str:
        return self._auth.identity_subject_hash(provider, subject)

    async def _by_subject(self, provider: str, subject: str, *, lock: bool = False):
        query = select(UserIdentity).where(
            UserIdentity.provider == provider,
            UserIdentity.subject_hash == self.subject_hash(provider, subject),
        )
        if lock:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    def _require_not_blocked(user) -> None:
        if UserAccessStateService.classify(user) == UserAccessState.BLOCKED:
            raise IdentityLinkError("user_blocked", status_code=403)

    async def _device_owner(self, installation_key_hash: str) -> int | None:
        """The user an active installation is currently bound to, if any."""

        if not installation_key_hash:
            return None
        result = await self.session.execute(
            select(DesktopDevice.user_id).where(
                DesktopDevice.installation_key_hash == installation_key_hash,
                DesktopDevice.revoked_at.is_(None),
            )
        )
        owner = result.scalar_one_or_none()
        return int(owner) if owner else None

    async def resolve_signin(
        self,
        verified: VerifiedIdentity,
        *,
        installation_key_hash: str,
    ) -> int:
        """Return the internal user id this provider identity may sign in as.

        Phase 1 never creates an account: Telegram remains the only user
        factory, so an unrecognised identity is told to sign in with Telegram
        once and connect the provider from Profile.
        """

        identity = await self._by_subject(
            verified.provider, verified.subject, lock=True
        )
        if identity is None:
            # Deliberately the same answer whether or not this device is
            # already bound to someone: a bound device is not consent.
            raise IdentityLinkError(
                "oauth_telegram_account_required", status_code=409
            )

        user_id = int(identity.user_id)
        owner = await self._device_owner(installation_key_hash)
        if owner is not None and owner != user_id:
            # Mirrors the existing poll_link precedent. Failing here gives the
            # client a clear "unlink this device first" message instead of an
            # opaque failure later in the token exchange.
            raise IdentityLinkError(
                "desktop_device_bound_to_other_user", status_code=409
            )

        user = await self.session.get(User, user_id)
        # Parity with the bot flow, which cannot be reached at all while
        # blocked. Without this, a provider identity linked before the block
        # would still mint fresh sessions.
        self._require_not_blocked(user)

        identity.last_login_at = _utcnow()
        # Apple only sends the display name on the first authorization, so a
        # later sign-in must never blank an existing one.
        if verified.display_name and not identity.display_name:
            identity.display_name = verified.display_name
        await self.session.flush()
        return user_id

    async def link_to_user(
        self,
        verified: VerifiedIdentity,
        *,
        user_id: int,
    ) -> UserIdentity:
        """Attach a verified identity to an already authenticated user."""

        user = await self.session.get(User, int(user_id))
        if not user:
            raise IdentityLinkError("oauth_identity_not_found", status_code=404)
        # A blocked account must not gain new ways in either.
        self._require_not_blocked(user)

        existing = await self._by_subject(
            verified.provider, verified.subject, lock=True
        )
        if existing is not None:
            if int(existing.user_id) == int(user_id):
                # Same person re-running the link; make it idempotent rather
                # than an error the UI has to explain.
                existing.last_login_at = _utcnow()
                await self.session.flush()
                return existing
            # NEVER reassign. See the module docstring.
            raise IdentityLinkError(
                "oauth_identity_bound_to_other_user", status_code=409
            )

        same_provider = await self.session.execute(
            select(UserIdentity).where(
                UserIdentity.user_id == int(user_id),
                UserIdentity.provider == verified.provider,
            )
        )
        if same_provider.scalar_one_or_none() is not None:
            raise IdentityLinkError(
                "oauth_identity_already_linked", status_code=409
            )

        identity = UserIdentity(
            id=str(uuid4()),
            user_id=int(user_id),
            provider=verified.provider,
            subject_hash=self.subject_hash(verified.provider, verified.subject),
            email_hash=self._auth.identity_email_hash(verified.email or ""),
            email_display=(verified.email or None),
            email_verified=bool(verified.email_verified),
            display_name=verified.display_name,
            audience=verified.audience,
            created_at=_utcnow(),
            last_login_at=_utcnow(),
        )
        self.session.add(identity)
        await self.session.flush()
        return identity

    async def list_identities(self, user_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(UserIdentity)
            .where(UserIdentity.user_id == int(user_id))
            .order_by(UserIdentity.created_at.asc())
        )
        return [
            {
                "id": row.id,
                "provider": row.provider,
                "email_masked": mask_email(row.email_display),
                "display_name": row.display_name,
                "linked_at": row.created_at.isoformat() if row.created_at else None,
                "last_login_at": (
                    row.last_login_at.isoformat() if row.last_login_at else None
                ),
            }
            for row in result.scalars().all()
        ]

    async def unlink(
        self,
        identity_id: str,
        *,
        user_id: int,
        keep_session_id: str | None = None,
    ) -> dict[str, Any]:
        result = await self.session.execute(
            select(UserIdentity)
            .where(UserIdentity.id == str(identity_id or ""))
            .with_for_update()
        )
        identity = result.scalar_one_or_none()
        # 404 rather than 403 for someone else's row: never confirm that an
        # identity id exists on another account.
        if identity is None or int(identity.user_id) != int(user_id):
            raise IdentityLinkError("oauth_identity_not_found", status_code=404)

        user = await self.session.get(User, int(user_id))
        remaining = await self.session.execute(
            select(UserIdentity).where(
                UserIdentity.user_id == int(user_id),
                UserIdentity.id != identity.id,
            )
        )
        has_other_identity = remaining.scalars().first() is not None
        # Phase 1 users always have Telegram, so this only bites once
        # telegram_id becomes nullable. Keeping it now means Phase 2 cannot
        # accidentally ship an account nobody can sign in to.
        if not has_other_identity and not (user and user.telegram_id):
            raise IdentityLinkError("oauth_last_identity", status_code=409)

        provider = identity.provider
        await self.session.delete(identity)
        await self.session.flush()

        # Removing an identity must end the access it could have created. We do
        # not track which identity minted which device, so revoke every other
        # session and say so in the UI copy.
        device_ids = (
            await self.session.execute(
                select(DesktopDevice.id).where(DesktopDevice.user_id == int(user_id))
            )
        ).scalars().all()
        revoked = 0
        if device_ids:
            now = _utcnow()
            conditions = [
                DesktopSession.device_id.in_(list(device_ids)),
                DesktopSession.revoked_at.is_(None),
            ]
            if keep_session_id:
                conditions.append(DesktopSession.id != str(keep_session_id))
            outcome = await self.session.execute(
                update(DesktopSession)
                .where(*conditions)
                .values(revoked_at=now)
                .execution_options(synchronize_session=False)
            )
            revoked = max(0, int(outcome.rowcount or 0))
        await self.session.flush()
        return {"ok": True, "provider": provider, "sessions_revoked": revoked}
