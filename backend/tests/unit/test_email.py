from app.core.config import settings
from app.utils.email import _from_header


def test_from_header_is_bare_address_when_no_display_name(monkeypatch):
    monkeypatch.setattr(settings, "smtp_from_email", "no-reply@example.com")
    monkeypatch.setattr(settings, "smtp_from_name", "")
    assert _from_header() == "no-reply@example.com"


def test_from_header_includes_display_name_when_set(monkeypatch):
    monkeypatch.setattr(settings, "smtp_from_email", "onboarding@example.com")
    monkeypatch.setattr(settings, "smtp_from_name", "Employee Portal")
    header = _from_header()
    assert str(header) == "Employee Portal <onboarding@example.com>"
