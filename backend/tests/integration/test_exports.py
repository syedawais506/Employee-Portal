"""CSV export endpoints across modules (Employees, Departments, Projects,
Clients): permission gating and filter correctness. See docs/ROADMAP.md.
"""


def test_employee_export_permission_and_filters(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")

    forbidden = client.get("/api/v1/employees/export", headers=headers_employee)
    assert forbidden.status_code == 403

    _, engineer, _ = tenant_a.users["Employee"]
    india_update = client.patch(
        f"/api/v1/employees/{engineer.id}", headers=headers_admin, json={"location": "India"}
    )
    assert india_update.status_code == 200

    all_export = client.get("/api/v1/employees/export", headers=headers_admin)
    assert all_export.status_code == 200
    assert all_export.headers["content-type"].startswith("text/csv")
    assert "employee@acme-demo.com" in all_export.text

    india_export = client.get("/api/v1/employees/export", headers=headers_admin, params={"location": "India"})
    assert "employee@acme-demo.com" in india_export.text
    assert "manager@acme-demo.com" not in india_export.text


def test_department_export_permission_and_search(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")

    forbidden = client.get("/api/v1/departments/export", headers=headers_employee)
    assert forbidden.status_code == 403

    export_response = client.get("/api/v1/departments/export", headers=headers_admin)
    assert export_response.status_code == 200
    assert "Engineering" in export_response.text

    filtered = client.get("/api/v1/departments/export", headers=headers_admin, params={"search": "Nonexistent"})
    assert "Engineering" not in filtered.text


def test_project_export_permission_and_filters(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_manager = tenant_a.auth_headers(client, "Manager")

    forbidden = client.get("/api/v1/projects/export", headers=headers_manager)
    assert forbidden.status_code == 403

    create_response = client.post(
        "/api/v1/projects", headers=headers_admin, json={"name": "Export Test Project", "is_billable": True}
    )
    assert create_response.status_code == 201

    export_response = client.get("/api/v1/projects/export", headers=headers_admin)
    assert export_response.status_code == 200
    assert "Export Test Project" in export_response.text

    billable_only = client.get("/api/v1/projects/export", headers=headers_admin, params={"is_billable": "false"})
    assert "Export Test Project" not in billable_only.text


def test_client_export_permission_and_search(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_manager = tenant_a.auth_headers(client, "Manager")

    forbidden = client.get("/api/v1/clients/export", headers=headers_manager)
    assert forbidden.status_code == 403

    create_response = client.post("/api/v1/clients", headers=headers_admin, json={"name": "Acme Export Client"})
    assert create_response.status_code == 201

    export_response = client.get("/api/v1/clients/export", headers=headers_admin)
    assert export_response.status_code == 200
    assert "Acme Export Client" in export_response.text
