"""Phase 9c: white-label onboarding branding (per-company logo + accent
color) and Company Tour (an Admin-authored ordered list of welcome slides),
both surfaced through the existing public `/onboarding/{token}` context
rather than a new public endpoint. Scope is deliberately narrowed to the
public onboarding experience only — see docs/ROADMAP.md.
"""

from app.services import onboarding_service as onboarding_service_module


class _CapturedInvites:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def delay(self, email: str, token: str) -> None:
        self.calls.append((email, token))


def _create_invited_employee(client, headers, monkeypatch, *, email="newhire@acme-demo.com"):
    captured = _CapturedInvites()
    monkeypatch.setattr(onboarding_service_module, "send_onboarding_invite_email", captured)

    response = client.post(
        "/api/v1/employees",
        headers=headers,
        json={"email": email, "first_name": "New", "last_name": "Hire", "employment_type": "full_time"},
    )
    assert response.status_code == 201, response.text
    _, raw_token = captured.calls[-1]
    return raw_token


# -- Branding: permission gating and color -----------------------------------


def test_branding_requires_onboarding_permission(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.get("/api/v1/branding", headers=headers_employee)
    assert response.status_code == 403


def test_admin_can_get_and_update_branding_color(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    initial = client.get("/api/v1/branding", headers=headers_admin)
    assert initial.status_code == 200
    assert initial.json()["primary_color"] is None
    assert initial.json()["logo_url"] is None

    updated = client.patch("/api/v1/branding/color", headers=headers_admin, json={"primary_color": "#4F46E5"})
    assert updated.status_code == 200
    assert updated.json()["primary_color"] == "#4F46E5"


def test_branding_color_must_be_a_hex_string(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    response = client.patch("/api/v1/branding/color", headers=headers_admin, json={"primary_color": "blue"})
    assert response.status_code == 422


def test_hr_cannot_configure_branding_but_can_view(client, tenant_a):
    headers_hr = tenant_a.auth_headers(client, "HR")
    view = client.get("/api/v1/branding", headers=headers_hr)
    assert view.status_code == 200

    configure = client.patch("/api/v1/branding/color", headers=headers_hr, json={"primary_color": "#000000"})
    assert configure.status_code == 403


def test_admin_can_upload_logo(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    response = client.post(
        "/api/v1/branding/logo",
        headers=headers_admin,
        files={"file": ("logo.png", b"\x89PNG\r\n\x1a\n fake logo bytes", "image/png")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["logo_url"] is not None


def test_logo_upload_rejects_non_image_content_type(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    response = client.post(
        "/api/v1/branding/logo",
        headers=headers_admin,
        files={"file": ("logo.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 422


# -- Company Tour: CRUD and permission gating --------------------------------


def test_tour_requires_onboarding_permission(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.get("/api/v1/company-tour", headers=headers_employee)
    assert response.status_code == 403


def test_admin_can_create_update_delete_tour_step(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    create = client.post(
        "/api/v1/company-tour",
        headers=headers_admin,
        data={"title": "Welcome", "body": "Glad to have you here.", "sort_order": "1"},
    )
    assert create.status_code == 201, create.text
    step_id = create.json()["id"]
    assert create.json()["image_url"] is None

    update = client.patch(
        f"/api/v1/company-tour/{step_id}", headers=headers_admin, json={"title": "Welcome aboard!"}
    )
    assert update.status_code == 200
    assert update.json()["title"] == "Welcome aboard!"

    listed = client.get("/api/v1/company-tour", headers=headers_admin)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    delete = client.delete(f"/api/v1/company-tour/{step_id}", headers=headers_admin)
    assert delete.status_code == 204

    listed_after = client.get("/api/v1/company-tour", headers=headers_admin).json()
    assert listed_after == []


def test_tour_step_can_include_an_image(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    create = client.post(
        "/api/v1/company-tour",
        headers=headers_admin,
        data={"title": "Our Culture", "body": "We value ownership.", "sort_order": "2"},
        files={"image": ("culture.jpg", b"\xff\xd8\xff fake jpg bytes", "image/jpeg")},
    )
    assert create.status_code == 201, create.text
    assert create.json()["image_url"] is not None


def test_manager_cannot_configure_tour_steps(client, tenant_a):
    headers_manager = tenant_a.auth_headers(client, "Manager")
    response = client.post(
        "/api/v1/company-tour", headers=headers_manager, data={"title": "x", "body": "y", "sort_order": "0"}
    )
    assert response.status_code == 403


# -- Public onboarding context: branding + tour surfaced ----------------------


def test_public_onboarding_context_includes_branding_and_ordered_tour_steps(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    client.patch("/api/v1/branding/color", headers=headers_admin, json={"primary_color": "#4F46E5"})
    client.post(
        "/api/v1/company-tour", headers=headers_admin, data={"title": "Second", "body": "b", "sort_order": "2"}
    )
    client.post(
        "/api/v1/company-tour", headers=headers_admin, data={"title": "First", "body": "a", "sort_order": "1"}
    )

    raw_token = _create_invited_employee(client, headers_admin, monkeypatch)
    context = client.get(f"/api/v1/onboarding/{raw_token}")
    assert context.status_code == 200, context.text
    body = context.json()

    assert body["company_branding"]["primary_color"] == "#4F46E5"
    assert body["company_branding"]["name"] == "Acme Corp"
    assert [step["title"] for step in body["tour_steps"]] == ["First", "Second"]


def test_public_onboarding_context_has_empty_defaults_when_unconfigured(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    raw_token = _create_invited_employee(client, headers_admin, monkeypatch)

    context = client.get(f"/api/v1/onboarding/{raw_token}").json()
    assert context["company_branding"]["primary_color"] is None
    assert context["company_branding"]["logo_url"] is None
    assert context["tour_steps"] == []


def test_branding_and_tour_isolated_per_company(client, tenant_a, tenant_b):
    headers_admin_a = tenant_a.auth_headers(client, "Admin")
    headers_admin_b = tenant_b.auth_headers(client, "Admin")
    client.patch("/api/v1/branding/color", headers=headers_admin_a, json={"primary_color": "#4F46E5"})
    client.post(
        "/api/v1/company-tour", headers=headers_admin_a, data={"title": "Acme Only", "body": "b", "sort_order": "1"}
    )

    branding_b = client.get("/api/v1/branding", headers=headers_admin_b)
    assert branding_b.json()["primary_color"] is None

    tour_b = client.get("/api/v1/company-tour", headers=headers_admin_b)
    assert tour_b.json() == []
