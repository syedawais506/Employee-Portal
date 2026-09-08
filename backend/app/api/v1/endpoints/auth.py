from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.exceptions import TokenError
from app.core.rate_limit import limiter
from app.models.user import User
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.auth import (
    CurrentUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services.ai_chatbot_service import ai_chatbot_service
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
employee_repo = EmployeeRepository()


def _set_refresh_cookie(response: Response, token: str, ttl_seconds: int) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=ttl_seconds,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax",
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.email, payload.password)
    access_token, expires_in, refresh_token, ttl = auth_service.issue_token_pair(
        db, user, remember_me=payload.remember_me
    )
    _set_refresh_cookie(response, refresh_token, int(ttl.total_seconds()))
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if refresh_token is None:
        raise TokenError("Missing refresh token")
    access_token, expires_in, new_refresh_token, ttl = auth_service.refresh_access_token(db, refresh_token)
    _set_refresh_cookie(response, new_refresh_token, int(ttl.total_seconds()))
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if refresh_token:
        auth_service.revoke_refresh_token(refresh_token)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")


@router.post("/forgot-password", status_code=202)
@limiter.limit(settings.auth_rate_limit)
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):  # noqa: ARG001
    auth_service.request_password_reset(db, payload.email)


@router.post("/reset-password", status_code=204)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, payload.token, payload.new_password)
    db.commit()


@router.post("/verify-email", status_code=204)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    auth_service.verify_email(db, payload.token)
    db.commit()


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    permissions = auth_service.get_effective_permissions(db, current_user.id)
    employee = employee_repo.get_by_user_id(db, current_user.id) if current_user.company_id else None
    ai_chatbot_enabled = (
        ai_chatbot_service.is_enabled(db, current_user.company_id) if current_user.company_id else False
    )
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        company_id=current_user.company_id,
        is_super_admin=current_user.is_super_admin,
        is_verified=current_user.is_verified,
        permissions=sorted(permissions),
        employee_id=employee.id if employee else None,
        full_name=employee.full_name if employee else None,
        ai_chatbot_enabled=ai_chatbot_enabled,
    )
