from app.core.config import settings
from app.tasks.celery_app import celery_app
from app.utils.email import send_email


@celery_app.task(name="send_verification_email")
def send_verification_email(to_email: str, token: str) -> None:
    link = f"{settings.frontend_base_url}/verify-email?token={token}"
    send_email(
        to=to_email,
        subject="Verify your email — Employee Portal",
        html_body=f"<p>Welcome! Please verify your email by clicking " f'<a href="{link}">this link</a>.</p>',
    )


@celery_app.task(name="send_password_reset_email")
def send_password_reset_email(to_email: str, token: str) -> None:
    link = f"{settings.frontend_base_url}/reset-password?token={token}"
    send_email(
        to=to_email,
        subject="Reset your password — Employee Portal",
        html_body=(
            f'<p>We received a request to reset your password. <a href="{link}">Click here</a> '
            "to choose a new one. This link expires in 30 minutes. If you didn't request this, "
            "you can ignore this email.</p>"
        ),
    )


@celery_app.task(name="send_onboarding_invite_email")
def send_onboarding_invite_email(to_email: str, token: str) -> None:
    link = f"{settings.frontend_base_url}/onboarding/{token}"
    send_email(
        to=to_email,
        subject="Welcome — complete your onboarding",
        html_body=(
            f'<p>Welcome aboard! Please complete your onboarding <a href="{link}">here</a>: '
            "set your password and upload the requested documents. This link expires in "
            "7 days.</p>"
        ),
    )

