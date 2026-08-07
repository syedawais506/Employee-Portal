def test_employee_role_cannot_delete_employee(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, target_employee, _ = tenant_a.users["HR"]

    response = client.delete(f"/api/v1/employees/{target_employee.id}", headers=headers_employee)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_role_can_delete_employee(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, target_employee, _ = tenant_a.users["Finance"]

    response = client.delete(f"/api/v1/employees/{target_employee.id}", headers=headers_admin)
    assert response.status_code == 204

    get_response = client.get(f"/api/v1/employees/{target_employee.id}", headers=headers_admin)
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "exited"


def test_employee_role_cannot_create_department(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.post("/api/v1/departments", headers=headers_employee, json={"name": "Shadow IT"})
    assert response.status_code == 403


def test_full_employee_crud_lifecycle_via_admin(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    create_response = client.post(
        "/api/v1/employees",
        headers=headers_admin,
        json={
            "email": "lifecycle@acme-demo.com",
            "first_name": "Lifecycle",
            "last_name": "Test",
            "department_id": str(tenant_a.department.id),
            "designation": "QA Engineer",
            "employment_type": "full_time",
            "joining_date": "2025-01-01",
        },
    )
    assert create_response.status_code == 201
    employee = create_response.json()
    assert employee["employee_code"]
    assert employee["department"]["id"] == str(tenant_a.department.id)

    update_response = client.patch(
        f"/api/v1/employees/{employee['id']}",
        headers=headers_admin,
        json={"designation": "Senior QA Engineer"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["designation"] == "Senior QA Engineer"

    list_response = client.get(
        "/api/v1/employees", headers=headers_admin, params={"search": "Lifecycle"}
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    delete_response = client.delete(f"/api/v1/employees/{employee['id']}", headers=headers_admin)
    assert delete_response.status_code == 204


def test_creating_employee_with_duplicate_email_returns_409(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    existing_user, _, _ = tenant_a.users["Employee"]

    response = client.post(
        "/api/v1/employees",
        headers=headers_admin,
        json={"email": existing_user.email, "first_name": "Dup", "last_name": "Licate"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_manager_from_another_company_is_rejected(client, tenant_a, tenant_b):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, foreign_manager, _ = tenant_b.users["Manager"]

    response = client.post(
        "/api/v1/employees",
        headers=headers_admin,
        json={
            "email": "cross.tenant@acme-demo.com",
            "first_name": "Cross",
            "last_name": "Tenant",
            "manager_id": str(foreign_manager.id),
        },
    )
    assert response.status_code == 422
