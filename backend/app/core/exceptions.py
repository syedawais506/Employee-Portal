from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class PermissionDeniedError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "PERMISSION_DENIED"


class ValidationAppError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "VALIDATION_ERROR"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class InvalidCredentialsError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "INVALID_CREDENTIALS"


class TokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "TOKEN_INVALID"


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


def register_exception_handlers(app) -> None:  # noqa: ANN001
    app.add_exception_handler(AppException, app_exception_handler)
