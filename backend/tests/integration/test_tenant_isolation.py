"""Cross-tenant isolation is the most safety-critical property of the
platform (see docs/SRS.md acceptance criteria #2). These tests assert it
holds through the real HTTP API, not just at the repository layer.
"""


def test_admin_cannot_list_across_companies(client, tenant_a, tenant_b):
    headers_a = tenant_a.auth_headers(client, "Admin")
    response = client.get("/api/v1/employees", headers=headers_a)
    assert response.status_code == 200
    codes_a = {item["employee_code"] for item in response.json()["items"]}
    codes_b = {emp.employee_code for _, emp, _ in tenant_b.users.values()}
    assert codes_a.isdisjoint(codes_b)


def test_admin_cannot_read_another_companys_employee_by_id(client, tenant_a, tenant_b):
    headers_a = tenant_a.auth_headers(client, "Admin")
    _, other_employee, _ = tenant_b.users["Employee"]

    response = client.get(f"/api/v1/employees/{other_employee.id}", headers=headers_a)
    assert response.status_code == 404


def test_admin_cannot_update_another_companys_employee(client, tenant_a, tenant_b):
    headers_a = tenant_a.auth_headers(client, "Admin")
    _, other_employee, _ = tenant_b.users["Employee"]

    response = client.patch(
        f"/api/v1/employees/{other_employee.id}", headers=headers_a, json={"designation": "Hacked"}
    )
    assert response.status_code == 404


def test_admin_cannot_delete_another_companys_employee(client, tenant_a, tenant_b):
    headers_a = tenant_a.auth_headers(client, "Admin")
    _, other_employee, _ = tenant_b.users["Employee"]

    response = client.delete(f"/api/v1/employees/{other_employee.id}", headers=headers_a)
    assert response.status_code == 404


def test_departments_are_isolated_per_company(client, tenant_a, tenant_b):
    headers_a = tenant_a.auth_headers(client, "Admin")
    response = client.get("/api/v1/departments", headers=headers_a)
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert str(tenant_b.department.id) not in ids


def test_roles_are_isolated_per_company(client, tenant_a, tenant_b):
    headers_a = tenant_a.auth_headers(client, "Admin")
    response = client.get("/api/v1/roles", headers=headers_a)
    assert response.status_code == 200
    role_ids = {item["id"] for item in response.json()}
    tenant_b_role_ids = {str(r.id) for r in tenant_b.roles.values()}
    assert role_ids.isdisjoint(tenant_b_role_ids)


def test_employee_created_in_company_a_not_visible_via_company_b_admin(client, tenant_a, tenant_b):
    headers_a = tenant_a.auth_headers(client, "Admin")
    create_response = client.post(
        "/api/v1/employees",
        headers=headers_a,
        json={
            "email": "new.hire@acme-demo.com",
            "first_name": "New",
            "last_name": "Hire",
            "employment_type": "full_time",
        },
    )
    assert create_response.status_code == 201
    new_employee_id = create_response.json()["id"]

    headers_b = tenant_b.auth_headers(client, "Admin")
    response = client.get(f"/api/v1/employees/{new_employee_id}", headers=headers_b)
    assert response.status_code == 404
