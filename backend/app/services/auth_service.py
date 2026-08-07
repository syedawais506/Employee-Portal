import uuid
from datetime import timedelta

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
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services import permission_cache
from app.services.audit_service import audit_service
from app.tasks.email_tasks import send_password_reset_email, send_verification_email

REFRESH_TOKEN_PREFIX = "refresh_jti:"
RESET_TOKEN_PREFIX = "reset_jti:"
VERIFY_TOKEN_PREFIX = "verify_jti:"


class AuthService:
    def __init__(self) -> None:
        self.user_repo = UserRepository()
        self.role_repo = RoleRepository()

    def authenticate(self, db: Session, email: str, password: str) -> User:
        from datetime import datetime, timezone

        user = self.user_repo.get_by_email(db, email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Incorrect email or password")
        if not user.is_active:
            raise InvalidCredentialsError("Account is deactivated")
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
        get_redis().setex(f"{REFRESH_TOKEN_PREFIX}{refresh_jti}", ttl, str(user.id))
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

        user = self.user_repo.get_by_id(db, uuid.UUID(user_id))
        if user is None or not user.is_active:
            raise TokenError("User no longer active")

        access_token, expires_in, new_refresh_token, ttl = self.issue_token_pair(db, user)
        return access_token, expires_in, new_refresh_token, ttl

    def revoke_refresh_token(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            return
        get_redis().delete(f"{REFRESH_TOKEN_PREFIX}{payload['jti']}")

    def revoke_all_refresh_tokens(self, user_id: str) -> None:
        # Refresh tokens are tracked individually by jti with no per-user index
        # in this minimal implementation; a production system would maintain
        # a per-user set of active jtis to revoke in bulk here.
        pass

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
