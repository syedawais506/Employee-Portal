import httpx

from app.tasks.celery_app import celery_app
from app.utils.url_safety import UnsafeWebhookURLError, validate_outbound_webhook_url


@celery_app.task(name="deliver_webhook", bind=True, max_retries=3)
def deliver_webhook(self, url: str, text: str) -> None:
    try:
        # Re-validated here, not just at save time in integration_service —
        # DNS can resolve differently between when an Admin saves the URL and
        # when this task actually runs it (DNS rebinding). A failure here is
        # not retried: if the URL is unsafe now, retrying won't make it safe.
        validate_outbound_webhook_url(url)
    except UnsafeWebhookURLError:
        return

    try:
        response = httpx.post(url, json={"text": text}, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise self.retry(exc=exc, countdown=60) from exc
