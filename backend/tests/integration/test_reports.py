"""Reporting (Phase 7): a cross-module report hub that reuses each module's
own report_rows()/export_csv() logic (no duplicated queries), on-screen
preview before committing to a CSV download, and saved filter sets that can
be re-run or exported later. See docs/ROADMAP.md.
"""


def test_preview_employee_report_with_filters(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    response = client.post(
        "/api/v1/reports/preview", headers=headers_admin, json={"module": "employee", "filters": {"status": "active"}}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["header"] == [
        "Employee Code", "First Name", "Last Name", "Email", "Department", "Designation",
        "Manager", "Employment Type", "Location", "Joining Date", "Status", "Onboarding Status",
    ]
    assert body["total"] == len(body["rows"])
    assert body["truncated"] is False


def test_preview_unknown_module_rejected(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    response = client.post("/api/v1/reports/preview", headers=headers_admin, json={"module": "bogus", "filters": {}})
    assert response.status_code == 422


def test_preview_invalid_filter_value_rejected(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    response = client.post(
        "/api/v1/reports/preview",
        headers=headers_admin,
        json={"module": "employee", "filters": {"department_id": "not-a-uuid"}},
    )
    assert response.status_code == 422


def test_export_returns_csv(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    response = client.post("/api/v1/reports/export", headers=headers_admin, json={"module": "leave", "filters": {}})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Employee,Leave Type,Start Date,End Date,Days,Status,Reason" in response.text


def test_saved_report_crud_and_run(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    create_response = client.post(
        "/api/v1/reports/saved",
        headers=headers_admin,
        json={"name": "Active Employees", "module": "employee", "filters": {"status": "active"}},
    )
    assert create_response.status_code == 201, create_response.text
    saved = create_response.json()
    assert saved["name"] == "Active Employees"

    duplicate = client.post(
        "/api/v1/reports/saved",
        headers=headers_admin,
        json={"name": "Active Employees", "module": "employee", "filters": {}},
    )
    assert duplicate.status_code == 409

    list_response = client.get("/api/v1/reports/saved", headers=headers_admin)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    run_response = client.post(f"/api/v1/reports/saved/{saved['id']}/run", headers=headers_admin)
    assert run_response.status_code == 200
    assert run_response.json()["total"] >= 0

    export_response = client.get(f"/api/v1/reports/saved/{saved['id']}/export", headers=headers_admin)
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")

    update_response = client.patch(
        f"/api/v1/reports/saved/{saved['id']}", headers=headers_admin, json={"name": "All Active Employees"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "All Active Employees"

    delete_response = client.delete(f"/api/v1/reports/saved/{saved['id']}", headers=headers_admin)
    assert delete_response.status_code == 204

    empty_list = client.get("/api/v1/reports/saved", headers=headers_admin)
    assert empty_list.json() == []


def test_saved_report_update_validates_filters_against_its_own_module(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    created = client.post(
        "/api/v1/reports/saved",
        headers=headers_admin,
        json={"name": "Asset Report", "module": "asset", "filters": {}},
    ).json()

    response = client.patch(
        f"/api/v1/reports/saved/{created['id']}",
        headers=headers_admin,
        json={"filters": {"asset_type_id": "not-a-uuid"}},
    )
    assert response.status_code == 422


def test_permission_gating_across_roles(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_hr = tenant_a.auth_headers(client, "HR")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_finance = tenant_a.auth_headers(client, "Finance")
    headers_employee = tenant_a.auth_headers(client, "Employee")

    preview_body = {"module": "employee", "filters": {}}

    # Employee has no report.* permission at all.
    assert client.post("/api/v1/reports/preview", headers=headers_employee, json=preview_body).status_code == 403

    # HR and Manager can preview but not export or configure saved reports.
    assert client.post("/api/v1/reports/preview", headers=headers_hr, json=preview_body).status_code == 200
    assert client.post("/api/v1/reports/export", headers=headers_hr, json=preview_body).status_code == 403
    assert client.post("/api/v1/reports/preview", headers=headers_manager, json=preview_body).status_code == 200
    assert client.post("/api/v1/reports/export", headers=headers_manager, json=preview_body).status_code == 403

    hr_create = client.post(
        "/api/v1/reports/saved", headers=headers_hr, json={"name": "HR Report", "module": "employee", "filters": {}}
    )
    assert hr_create.status_code == 403

    # Finance can preview and export but not configure saved reports.
    assert client.post("/api/v1/reports/preview", headers=headers_finance, json=preview_body).status_code == 200
    assert client.post("/api/v1/reports/export", headers=headers_finance, json=preview_body).status_code == 200
    finance_create = client.post(
        "/api/v1/reports/saved",
        headers=headers_finance,
        json={"name": "Finance Report", "module": "employee", "filters": {}},
    )
    assert finance_create.status_code == 403

    # Admin can do everything.
    admin_create = client.post(
        "/api/v1/reports/saved",
        headers=headers_admin,
        json={"name": "Admin Report", "module": "employee", "filters": {}},
    )
    assert admin_create.status_code == 201


def test_saved_reports_isolated_per_company(client, tenant_a, tenant_b):
    headers_admin_a = tenant_a.auth_headers(client, "Admin")
    client.post(
        "/api/v1/reports/saved",
        headers=headers_admin_a,
        json={"name": "Company A Report", "module": "employee", "filters": {}},
    )

    headers_admin_b = tenant_b.auth_headers(client, "Admin")
    list_b = client.get("/api/v1/reports/saved", headers=headers_admin_b)
    assert list_b.status_code == 200
    assert list_b.json() == []
