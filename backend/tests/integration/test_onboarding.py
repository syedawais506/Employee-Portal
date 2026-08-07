"""End-to-end onboarding workflow: HR/Admin creates an employee -> invite
email queued -> new hire sets a password and uploads documents via the
public token endpoints -> HR reviews documents -> Admin activates the
account. See docs/ROADMAP.md Phase 2.
"""

from app.services import onboarding_service as onboarding_service_module


class _CapturedInvites:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def delay(self, email: str, token: str) -> None:
        self.calls.append((email, token))


def _create_document_type(client, headers, name="Resume"):
    response = client.post(
        "/api/v1/document-types", headers=headers, json={"name": name, "is_required": True, "sort_order": 1}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_invited_employee(client, headers, monkeypatch, *, email="newhire@acme-demo.com"):
    captured = _CapturedInvites()
    monkeypatch.setattr(onboarding_service_module, "send_onboarding_invite_email", captured)

    response = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"email": email, "first_name": "New", "last_name": "Hire", "employment_type": "full_time"},
    )
    assert response.status_code == 201, response.text
    assert captured.calls, "creating an employee should queue an onboarding invite email"
    _, raw_token = captured.calls[-1]
    return response.json(), raw_token


def test_full_onboarding_workflow_activates_the_account(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    document_type_id = _create_document_type(client, headers_admin)
    employee, raw_token = _create_invited_employee(client, headers_admin, monkeypatch)
    employee_id = employee["id"]

    assert employee["onboarding_status"] == "invited"

    # The new hire's account can't log in yet — it isn't activated.
    blocked_login = client.post(
        "/api/v1/auth/login", json={"email": "newhire@acme-demo.com", "password": "irrelevant"}
    )
    assert blocked_login.status_code == 401

    context = client.get(f"/api/v1/onboarding/{raw_token}")
    assert context.status_code == 200
    assert context.json()["password_already_set"] is False
    assert context.json()["employee"]["onboarding_status"] == "invited"

    set_password = client.post(f"/api/v1/onboarding/{raw_token}/password", json={"password": "NewHirePass1"})
    assert set_password.status_code == 204

    upload = client.post(
        f"/api/v1/onboarding/{raw_token}/documents",
        data={"document_type_id": document_type_id},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake resume content", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    # Uploading the only required document (with a password already set)
    # should auto-advance the employee to "submitted".
    context_after_upload = client.get(f"/api/v1/onboarding/{raw_token}").json()
    assert context_after_upload["employee"]["onboarding_status"] == "submitted"

    queue = client.get("/api/v1/onboarding/queue", headers=headers_admin)
    assert any(item["id"] == employee_id for item in queue.json())

    documents = client.get(f"/api/v1/employees/{employee_id}/documents", headers=headers_admin)
    document_id = documents.json()[0]["id"]

    # HR can't sign off before reviewing the document.
    premature_hr_approve = client.post(f"/api/v1/employees/{employee_id}/onboarding/hr-approve", headers=headers_admin)
    assert premature_hr_approve.status_code == 422

    review = client.post(
        f"/api/v1/employees/{employee_id}/documents/{document_id}/review",
        headers=headers_admin,
        json={"approve": True},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "approved"

    hr_approve = client.post(f"/api/v1/employees/{employee_id}/onboarding/hr-approve", headers=headers_admin)
    assert hr_approve.status_code == 200
    assert hr_approve.json()["onboarding_status"] == "hr_approved"

    # Admin can't activate before HR has signed off (re-check with a fresh employee later);
    # here we're already past that gate, so activation should succeed.
    admin_approve = client.post(f"/api/v1/employees/{employee_id}/onboarding/approve", headers=headers_admin)
    assert admin_approve.status_code == 200
    assert admin_approve.json()["onboarding_status"] == "completed"

    activated_login = client.post(
        "/api/v1/auth/login", json={"email": "newhire@acme-demo.com", "password": "NewHirePass1"}
    )
    assert activated_login.status_code == 200


def test_admin_approve_blocked_before_hr_approval(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    employee, _ = _create_invited_employee(client, headers_admin, monkeypatch)

    response = client.post(f"/api/v1/employees/{employee['id']}/onboarding/approve", headers=headers_admin)
    assert response.status_code == 422


def test_employee_role_cannot_view_onboarding_queue(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.get("/api/v1/onboarding/queue", headers=headers_employee)
    assert response.status_code == 403


def test_expired_or_unknown_onboarding_token_is_rejected(client):
    response = client.get("/api/v1/onboarding/not-a-real-token")
    assert response.status_code == 401


def test_document_types_isolated_per_company(client, tenant_a, tenant_b):
    headers_a = tenant_a.auth_headers(client, "Admin")
    _create_document_type(client, headers_a, name="Resume")

    headers_b = tenant_b.auth_headers(client, "Admin")
    response = client.get("/api/v1/document-types", headers=headers_b)
    assert response.status_code == 200
    assert response.json() == []


def test_onboarding_queue_isolated_per_company(client, tenant_a, tenant_b, monkeypatch):
    headers_a = tenant_a.auth_headers(client, "Admin")
    employee, _ = _create_invited_employee(client, headers_a, monkeypatch)

    headers_b = tenant_b.auth_headers(client, "Admin")
    queue_b = client.get("/api/v1/onboarding/queue", headers=headers_b)
    assert all(item["id"] != employee["id"] for item in queue_b.json())


def test_offer_letter_download_returns_a_pdf(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, employee, _ = tenant_a.users["Employee"]

    response = client.get(f"/api/v1/employees/{employee.id}/offer-letter", headers=headers_admin)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
