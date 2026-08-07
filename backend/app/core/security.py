import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def _encode(payload: dict[str, Any], expires_delta: timedelta) -> tuple[str, str]:
    jti = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    to_encode = {
        **payload,
        "iat": now,
        "exp": now + expires_delta,
        "jti": jti,
    }
    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def create_access_token(*, user_id: str, company_id: str | None, role_ids: list[str]) -> tuple[str, str, int]:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    token, jti = _encode(
        {
            "sub": user_id,
            "company_id": company_id,
            "role_ids": role_ids,
            "type": TokenType.ACCESS.value,
        },
        expires_delta,
    )
    return token, jti, int(expires_delta.total_seconds())


def create_refresh_token(*, user_id: str, remember_me: bool = False) -> tuple[str, str, timedelta]:
    days = (
        settings.refresh_token_remember_me_expire_days
        if remember_me
        else settings.refresh_token_expire_days
    )
    expires_delta = timedelta(days=days)
    token, jti = _encode({"sub": user_id, "type": TokenType.REFRESH.value}, expires_delta)
    return token, jti, expires_delta


def create_short_lived_token(*, user_id: str, token_type: TokenType, minutes: int) -> tuple[str, str]:
    token, jti = _encode({"sub": user_id, "type": token_type.value}, timedelta(minutes=minutes))
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)
