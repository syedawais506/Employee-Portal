"""Phase 7c: daily digest reminders (work anniversaries, document expiry) and
outbound Slack/Teams webhooks.

The digest task (`run_daily_digest`) opens its own `SessionLocal()` per the
same pattern used by the notifications WebSocket endpoint, which — per the
docstring in test_notifications.py — is invisible to this suite's
SAVEPOINT-wrapped `db_session` fixture under READ COMMITTED isolation. So
these tests call the digest's `_notify_anniversaries`/`_notify_expiring_documents`
helpers directly against `db_session` (the same connection the `client`
fixture uses), rather than invoking `run_daily_digest()` itself. That's a
legitimate seam, not a workaround: `run_daily_digest()` is just per-company
session/transaction plumbing around these two functions, mirroring the
already-accepted untested plumbing in the WS endpoint.
"""

import uuid
from datetime import date

from app.core.security import hash_password
from app.models.onboarding import EmployeeDocument
from app.services import onboarding_service as onboarding_service_module
from app.tasks import digest_tasks as digest_tasks_module
from app.tasks import webhook_tasks as webhook_tasks_module


class _CapturedWebhooks:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def __call__(self, url, json=None, timeout=None):
        self.calls.append((url, json["text"]))

        class _Resp:
            def raise_for_status(self) -> None:
                pass

        return _Resp()


def _capture_webhooks(monkeypatch) -> _CapturedWebhooks:
    captured = _CapturedWebhooks()
    monkeypatch.setattr(webhook_tasks_module.httpx, "post", captured)
    return captured


def _notification_types(client, headers) -> list[str]:
    response = client.get("/api/v1/notifications", headers=headers)
    assert response.status_code == 200, response.text
    return [n["type"] for n in response.json()["items"]]


# -- Integrations endpoint: permission gating and settings CRUD --------------


def test_integrations_requires_company_configure_permission(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.get("/api/v1/integrations/slack", headers=headers_employee)
    assert response.status_code == 403


def test_admin_can_get_and_update_slack_webhook(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    initial = client.get("/api/v1/integrations/slack", headers=headers_admin)
    assert initial.status_code == 200
    assert initial.json()["slack_webhook_url"] is None

    updated = client.patch(
        "/api/v1/integrations/slack",
        headers=headers_admin,
        json={"slack_webhook_url": "https://hooks.slack.com/services/test"},
    )
    assert updated.status_code == 200
    assert updated.json()["slack_webhook_url"] == "https://hooks.slack.com/services/test"

    refetched = client.get("/api/v1/integrations/slack", headers=headers_admin)
    assert refetched.json()["slack_webhook_url"] == "https://hooks.slack.com/services/test"


def test_send_test_message_no_op_when_unconfigured(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    captured = _capture_webhooks(monkeypatch)

    response = client.post("/api/v1/integrations/slack/test", headers=headers_admin)
    assert response.status_code == 200
    assert response.json()["sent"] is False
    assert captured.calls == []


def test_send_test_message_posts_when_configured(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    captured = _capture_webhooks(monkeypatch)

    client.patch(
        "/api/v1/integrations/slack",
        headers=headers_admin,
        json={"slack_webhook_url": "https://hooks.slack.com/services/test"},
    )
    response = client.post("/api/v1/integrations/slack/test", headers=headers_admin)
    assert response.status_code == 200
    assert response.json()["sent"] is True
    assert len(captured.calls) == 1
    assert captured.calls[0][0] == "https://hooks.slack.com/services/test"


# -- Webhook dispatch on existing notification trigger points ----------------


def test_leave_submission_dispatches_webhook_when_configured(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    _, manager, _ = tenant_a.users["Manager"]
    captured = _capture_webhooks(monkeypatch)

    client.patch(f"/api/v1/employees/{engineer.id}", headers=headers_admin, json={"manager_id": str(manager.id)})
    client.patch(
        "/api/v1/integrations/slack", headers=headers_admin, json={"slack_webhook_url": "https://hooks.slack.com/services/test"}
    )
    leave_type = client.post(
        "/api/v1/leave-types",
        headers=headers_admin,
        json={
            "name": "Annual Leave",
            "is_paid": True,
            "annual_quota_days": 20,
            "max_carry_forward_days": 5,
            "requires_attachment": False,
        },
    ).json()

    response = client.post(
        "/api/v1/leave-requests",
        headers=headers_employee,
        data={"leave_type_id": leave_type["id"], "start_date": "2026-06-01", "end_date": "2026-06-01"},
    )
    assert response.status_code == 201, response.text
    assert len(captured.calls) == 1


def test_no_webhook_dispatched_when_unconfigured(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    _, manager, _ = tenant_a.users["Manager"]
    captured = _capture_webhooks(monkeypatch)

    client.patch(f"/api/v1/employees/{engineer.id}", headers=headers_admin, json={"manager_id": str(manager.id)})
    leave_type = client.post(
        "/api/v1/leave-types",
        headers=headers_admin,
        json={
            "name": "Annual Leave",
            "is_paid": True,
            "annual_quota_days": 20,
            "max_carry_forward_days": 5,
            "requires_attachment": False,
        },
    ).json()
    response = client.post(
        "/api/v1/leave-requests",
        headers=headers_employee,
        data={"leave_type_id": leave_type["id"], "start_date": "2026-06-01", "end_date": "2026-06-01"},
    )
    assert response.status_code == 201, response.text
    assert captured.calls == []


def test_fanout_notification_dispatches_webhook_exactly_once(client, tenant_a, db_session, monkeypatch):
    """onboarding.submitted fans out to every HR-permission holder — with two
    HR users, the in-app feed should have two rows but the shared Slack
    channel should only get pinged once per event, not once per recipient.
    """
    headers_admin = tenant_a.auth_headers(client, "Admin")
    captured = _capture_webhooks(monkeypatch)

    client.patch(
        "/api/v1/integrations/slack", headers=headers_admin, json={"slack_webhook_url": "https://hooks.slack.com/services/test"}
    )

    second_hr_user = tenant_a.user_repo.create(
        db_session,
        company_id=tenant_a.company.id,
        email="hr2@acme-demo.com",
        password_hash=hash_password("Password@123"),
        is_active=True,
        is_verified=True,
    )
    tenant_a.user_repo.assign_roles(db_session, second_hr_user.id, [tenant_a.roles["HR"].id])
    tenant_a.employee_repo.create(
        db_session,
        tenant_a.company.id,
        user_id=second_hr_user.id,
        employee_code=tenant_a.employee_repo.next_employee_code(db_session, tenant_a.company.id, "ACME"),
        first_name="Second",
        last_name="HR",
        employment_type="full_time",
        status="active",
    )
    db_session.commit()

    doc_type = client.post(
        "/api/v1/document-types", headers=headers_admin, json={"name": "Resume", "is_required": True, "sort_order": 1}
    ).json()
    employee_payload = {
        "email": "fanout-newhire@acme-demo.com",
        "first_name": "New",
        "last_name": "Hire",
        "employment_type": "full_time",
    }

    class _CapturedInvites:
        def __init__(self):
            self.calls: list[tuple[str, str]] = []

        def delay(self, email: str, token: str) -> None:
            self.calls.append((email, token))

    captured_invites = _CapturedInvites()
    monkeypatch.setattr(onboarding_service_module, "send_onboarding_invite_email", captured_invites)

    create_response = client.post("/api/v1/employees", headers=headers_admin, json=employee_payload)
    assert create_response.status_code == 201, create_response.text
    _, raw_token = captured_invites.calls[-1]
    client.post(f"/api/v1/onboarding/{raw_token}/password", json={"password": "NewHirePass1"})
    upload = client.post(
        f"/api/v1/onboarding/{raw_token}/documents",
        data={"document_type_id": doc_type["id"]},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    login_second_hr = client.post("/api/v1/auth/login", json={"email": "hr2@acme-demo.com", "password": "Password@123"})
    headers_second_hr = {"Authorization": f"Bearer {login_second_hr.json()['access_token']}"}
    headers_hr = tenant_a.auth_headers(client, "HR")

    assert "onboarding.submitted" in _notification_types(client, headers_hr)
    assert "onboarding.submitted" in _notification_types(client, headers_second_hr)
    assert len(captured.calls) == 1


# -- Digest: work anniversaries -----------------------------------------------


def test_anniversary_digest_notifies_matching_employee(client, tenant_a, db_session):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    engineer.joining_date = date(2020, 6, 15)
    db_session.commit()

    digest_tasks_module._notify_anniversaries(db_session, tenant_a.company.id, date(2026, 6, 15))

    assert "employee.anniversary" in _notification_types(client, headers_employee)


def test_anniversary_digest_skips_non_matching_and_same_year(client, tenant_a, db_session):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]

    engineer.joining_date = date(2020, 6, 15)
    db_session.commit()
    digest_tasks_module._notify_anniversaries(db_session, tenant_a.company.id, date(2026, 6, 16))
    assert "employee.anniversary" not in _notification_types(client, headers_employee)

    engineer.joining_date = date(2026, 6, 15)
    db_session.commit()
    digest_tasks_module._notify_anniversaries(db_session, tenant_a.company.id, date(2026, 6, 15))
    assert "employee.anniversary" not in _notification_types(client, headers_employee)


# -- Digest: document expiry --------------------------------------------------


def test_document_expiry_digest_notifies_hr_at_exact_lead_time(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_hr = tenant_a.auth_headers(client, "HR")

    doc_type = client.post(
        "/api/v1/document-types", headers=headers_admin, json={"name": "Visa", "is_required": True, "sort_order": 1}
    ).json()
    _, engineer, _ = tenant_a.users["Employee"]

    document = EmployeeDocument(
        company_id=tenant_a.company.id,
        employee_id=engineer.id,
        document_type_id=uuid.UUID(doc_type["id"]),
        file_key="fake/key.pdf",
        original_filename="visa.pdf",
        content_type="application/pdf",
        size_bytes=100,
        status="approved",
    )
    db_session.add(document)
    db_session.flush()
    document.expiry_date = date(2026, 6, 22)
    db_session.commit()

    today = date(2026, 6, 15)
    digest_tasks_module._notify_expiring_documents(db_session, tenant_a.company.id, today)

    assert "document.expiring" in _notification_types(client, headers_hr)


def test_document_expiry_digest_skips_documents_outside_lead_window(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_hr = tenant_a.auth_headers(client, "HR")

    doc_type = client.post(
        "/api/v1/document-types", headers=headers_admin, json={"name": "Visa", "is_required": True, "sort_order": 1}
    ).json()
    _, engineer, _ = tenant_a.users["Employee"]

    document = EmployeeDocument(
        company_id=tenant_a.company.id,
        employee_id=engineer.id,
        document_type_id=uuid.UUID(doc_type["id"]),
        file_key="fake/key.pdf",
        original_filename="visa.pdf",
        content_type="application/pdf",
        size_bytes=100,
        status="approved",
        expiry_date=date(2026, 6, 30),
    )
    db_session.add(document)
    db_session.commit()

    digest_tasks_module._notify_expiring_documents(db_session, tenant_a.company.id, date(2026, 6, 15))

    assert "document.expiring" not in _notification_types(client, headers_hr)
