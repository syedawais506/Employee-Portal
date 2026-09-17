import uuid
from datetime import timedelta
from typing import cast

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidCredentialsError, TokenError
from app.core.redis_client import get_redis
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    create_short_lived_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services import permission_cache
from app.tasks.email_tasks import send_password_reset_email, send_verification_email

REFRESH_TOKEN_PREFIX = "refresh_jti:"
RESET_TOKEN_PREFIX = "reset_jti:"
VERIFY_TOKEN_PREFIX = "verify_jti:"
REFRESH_USER_INDEX_PREFIX = "refresh_user:"
# Longer than the longest possible refresh-token TTL (30-day remember-me) so
# the per-user jti index outlives every token it could ever need to track;
# refreshed on every touch so an active user's index never actually expires.
REFRESH_USER_INDEX_TTL_SECONDS = 31 * 24 * 60 * 60


class AuthService:
    def __init__(self) -> None:
        self.user_repo = UserRepository()
        self.role_repo = RoleRepository()
        self.company_repo = CompanyRepository()

    def check_company_active(self, db: Session, company_id: uuid.UUID) -> None:
        """Super Admin has no company_id and never goes through this check.
        Everyone else's company must be active — neither suspended (Super
        Admin's Suspend action on the Companies page) nor soft-deleted.
        """
        company = self.company_repo.get(db, company_id)
        if company is None or company.deleted_at is not None or company.status != "active":
            raise InvalidCredentialsError("Your company's account is not currently active")

    def authenticate(self, db: Session, email: str, password: str) -> User:
        from datetime import datetime, timezone

        user = self.user_repo.get_by_email(db, email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Incorrect email or password")
        if not user.is_active:
            raise InvalidCredentialsError("Account is deactivated")
        if user.company_id is not None:
            self.check_company_active(db, user.company_id)
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        return user

    def issue_token_pair(self, db: Session, user: User, remember_me: bool = False):
        role_ids = [str(rid) for rid in self.user_repo.get_role_ids(db, user.id)]
        access_token, _, expires_in = create_access_token(
            user_id=str(user.id),
            company_id=str(user.company_id) if user.company_id else None,
            role_ids=role_ids,
        )
        refresh_token, refresh_jti, ttl = create_refresh_token(
            user_id=str(user.id), remember_me=remember_me
        )
        redis_client = get_redis()
        redis_client.setex(f"{REFRESH_TOKEN_PREFIX}{refresh_jti}", ttl, str(user.id))
        user_index_key = f"{REFRESH_USER_INDEX_PREFIX}{user.id}"
        redis_client.sadd(user_index_key, refresh_jti)
        redis_client.expire(user_index_key, REFRESH_USER_INDEX_TTL_SECONDS)
        return access_token, expires_in, refresh_token, ttl

    def refresh_access_token(self, db: Session, refresh_token: str):
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise TokenError("Invalid refresh token") from exc
        if payload.get("type") != TokenType.REFRESH.value:
            raise TokenError("Invalid token type")

        jti = payload["jti"]
        user_id = payload["sub"]
        redis_client = get_redis()
        key = f"{REFRESH_TOKEN_PREFIX}{jti}"
        stored = redis_client.get(key)

        if stored is None:
            # Token unknown: either expired naturally or already rotated/reused.
            # Reuse-detection: revoke all sessions for this user defensively.
            self.revoke_all_refresh_tokens(user_id)
            raise TokenError("Refresh token is no longer valid")

        redis_client.delete(key)  # rotate: old jti can never be used again
        redis_client.srem(f"{REFRESH_USER_INDEX_PREFIX}{user_id}", jti)

        user = self.user_repo.get_by_id(db, uuid.UUID(user_id))
        if user is None or not user.is_active:
            raise TokenError("User no longer active")
        if user.company_id is not None:
            try:
                self.check_company_active(db, user.company_id)
            except InvalidCredentialsError as exc:
                raise TokenError(str(exc)) from exc

        access_token, expires_in, new_refresh_token, ttl = self.issue_token_pair(db, user)
        return access_token, expires_in, new_refresh_token, ttl

    def revoke_refresh_token(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            return
        jti = payload["jti"]
        user_id = payload.get("sub")
        redis_client = get_redis()
        redis_client.delete(f"{REFRESH_TOKEN_PREFIX}{jti}")
        if user_id:
            redis_client.srem(f"{REFRESH_USER_INDEX_PREFIX}{user_id}", jti)

    def revoke_all_refresh_tokens(self, user_id: str) -> None:
        """Reuse-detection safety net: a replayed/stolen refresh token means
        every other still-active token for this user is suspect too, so all
        of them are invalidated, not just the one caught being reused.
        Requires every issued token's jti to have been added to this user's
        index at issue time (see issue_token_pair) — nothing here relies on
        enumerating Redis globally.
        """
        redis_client = get_redis()
        index_key = f"{REFRESH_USER_INDEX_PREFIX}{user_id}"
        # smembers() is typed as Union[Awaitable[Set], Set] in redis-py's shared
        # sync/async mixin even on this sync client — cast to the concrete
        # sync return type so mypy allows iterating over it below.
        jtis = cast("set[str]", redis_client.smembers(index_key))
        if jtis:
            redis_client.delete(*(f"{REFRESH_TOKEN_PREFIX}{jti}" for jti in jtis))
        redis_client.delete(index_key)

    def request_password_reset(self, db: Session, email: str) -> None:
        user = self.user_repo.get_by_email(db, email)
        if user is None:
            return  # never reveal whether an email exists
        token, jti = create_short_lived_token(
            user_id=str(user.id), token_type=TokenType.PASSWORD_RESET, minutes=30
        )
        get_redis().setex(f"{RESET_TOKEN_PREFIX}{jti}", timedelta(minutes=30), str(user.id))
        send_password_reset_email.delay(user.email, token)

    def reset_password(self, db: Session, token: str, new_password: str) -> None:
        try:
            payload = decode_token(token)
        except ValueError as exc:
            raise TokenError("Invalid or expired reset token") from exc
        if payload.get("type") != TokenType.PASSWORD_RESET.value:
            raise TokenError("Invalid token type")

        redis_client = get_redis()
        key = f"{RESET_TOKEN_PREFIX}{payload['jti']}"
        if redis_client.get(key) is None:
            raise TokenError("Reset token already used or expired")
        redis_client.delete(key)

        user = self.user_repo.get_by_id(db, uuid.UUID(payload["sub"]))
        if user is None:
            raise TokenError("User not found")
        user.password_hash = hash_password(new_password)
        user.is_verified = True  # only the mailbox owner could have opened this link
        db.flush()

    def send_verification_email(self, user: User) -> None:
        token, jti = create_short_lived_token(
            user_id=str(user.id), token_type=TokenType.EMAIL_VERIFY, minutes=60 * 24
        )
        get_redis().setex(f"{VERIFY_TOKEN_PREFIX}{jti}", timedelta(hours=24), str(user.id))
        send_verification_email.delay(user.email, token)

    def verify_email(self, db: Session, token: str) -> None:
        try:
            payload = decode_token(token)
        except ValueError as exc:
            raise TokenError("Invalid or expired verification token") from exc
        if payload.get("type") != TokenType.EMAIL_VERIFY.value:
            raise TokenError("Invalid token type")

        redis_client = get_redis()
        key = f"{VERIFY_TOKEN_PREFIX}{payload['jti']}"
        if redis_client.get(key) is None:
            raise TokenError("Verification token already used or expired")
        redis_client.delete(key)

        user = self.user_repo.get_by_id(db, uuid.UUID(payload["sub"]))
        if user is None:
            raise TokenError("User not found")
        user.is_verified = True
        db.flush()

    def get_effective_permissions(self, db: Session, user_id: uuid.UUID) -> set[str]:
        return permission_cache.get_effective_permissions(db, user_id, self.role_repo)


auth_service = AuthService()
