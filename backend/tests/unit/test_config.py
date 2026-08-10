from app.core.config import settings


def test_s3_public_endpoint_falls_back_to_internal_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "s3_endpoint_url", "http://minio:9000")
    monkeypatch.setattr(settings, "s3_public_endpoint_url", "")
    assert settings.s3_public_endpoint_url_effective == "http://minio:9000"


def test_s3_public_endpoint_overrides_internal_endpoint_when_set(monkeypatch):
    monkeypatch.setattr(settings, "s3_endpoint_url", "http://minio:9000")
    monkeypatch.setattr(settings, "s3_public_endpoint_url", "http://localhost:9000")
    assert settings.s3_public_endpoint_url_effective == "http://localhost:9000"
