import uuid
from collections.abc import Generator

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidCredentialsError, PermissionDeniedError, TokenError
from app.core.security import TokenType, decode_token
from app.db.rls import set_tenant_context
from app.db.session import SessionLocal
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

_user_repo = UserRepository()


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise InvalidCredentialsError("Not authenticated")
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise TokenError("Invalid or expired token") from exc
    if payload.get("type") != TokenType.ACCESS.value:
        raise TokenError("Invalid token type")

    user = _user_repo.get_by_id(db, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise InvalidCredentialsError("User not found or inactive")

    request.state.company_id = user.company_id
    set_tenant_context(db, str(user.company_id) if user.company_id else None)
    return user


def get_current_company_id(current_user: User = Depends(get_current_user)) -> uuid.UUID:
    if current_user.company_id is None:
        raise PermissionDeniedError("This action requires a company context")
    return current_user.company_id


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_super_admin:
        raise PermissionDeniedError("Super admin access required")
    return current_user


def require_permission(module: str, action: str):
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.is_super_admin:
            return current_user
        permissions = auth_service.get_effective_permissions(db, current_user.id)
        if f"{module}.{action}" not in permissions:
            raise PermissionDeniedError(f"Missing permission: {module}.{action}")
        return current_user

    return dependency
