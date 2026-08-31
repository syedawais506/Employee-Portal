import httpx

from app.tasks.celery_app import celery_app


@celery_app.task(name="deliver_webhook", bind=True, max_retries=3)
def deliver_webhook(self, url: str, text: str) -> None:
    try:
        response = httpx.post(url, json={"text": text}, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise self.retry(exc=exc, countdown=60) from exc
