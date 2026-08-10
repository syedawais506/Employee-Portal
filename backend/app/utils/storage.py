import uuid
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@lru_cache
def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


@lru_cache
def get_s3_presign_client():
    """A second client, identical except for endpoint_url, used only for
    generating presigned download URLs. SigV4 signs the Host header, so a
    presigned URL is only valid for the host it was signed against — using
    the internal Docker hostname (S3_ENDPOINT_URL) here would produce a URL
    the browser can't even resolve, let alone one MinIO would accept if it
    could. S3_PUBLIC_ENDPOINT_URL must be reachable from wherever the
    browser runs, not just from inside the Docker network.
    """
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_endpoint_url_effective,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists() -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket_name)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket_name)


def build_document_key(
    *, company_id: uuid.UUID, employee_id: uuid.UUID, document_type_id: uuid.UUID, filename: str
) -> str:
    safe_name = filename.replace("/", "_")
    return f"{company_id}/employees/{employee_id}/documents/{document_type_id}/{uuid.uuid4().hex}_{safe_name}"


def upload_document(*, key: str, content: bytes, content_type: str) -> None:
    get_s3_client().put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=content,
        ContentType=content_type,
    )


def generate_download_url(*, key: str, expires_in_seconds: int = 300) -> str:
    return get_s3_presign_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": key},
        ExpiresIn=expires_in_seconds,
    )
