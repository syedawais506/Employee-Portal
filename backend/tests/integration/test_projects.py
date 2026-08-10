"""Projects & Employee Mapping (Phase 3): client + project CRUD, member
assignment, tenant isolation, RBAC, and the self-service "my projects" view.
See docs/ROADMAP.md Phase 3.
"""


def _create_client(client, headers, name="Northwind Trading Co"):
    response = client.post("/api/v1/clients", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_full_project_lifecycle_with_members(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    client_id = _create_client(client, headers_admin)
    _, manager_employee, _ = tenant_a.users["Manager"]
    _, engineer_employee, _ = tenant_a.users["Employee"]

    create_response = client.post(
        "/api/v1/projects",
        headers=headers_admin,
        json={
            "name": "Website Revamp",
            "client_id": client_id,
            "budget": "50000.00",
            "is_billable": True,
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "member_ids": [{"employee_id": str(manager_employee.id), "role_on_project": "manager"}],
        },
    )
    assert create_response.status_code == 201, create_response.text
    project = create_response.json()
    assert project["client"]["id"] == client_id
    assert len(project["members"]) == 1

    project_id = project["id"]

    add_member_response = client.post(
        f"/api/v1/projects/{project_id}/members",
        headers=headers_admin,
        json={"employee_id": str(engineer_employee.id), "role_on_project": "member"},
    )
    assert add_member_response.status_code == 200
    assert len(add_member_response.json()["members"]) == 2

    remove_member_response = client.delete(
        f"/api/v1/projects/{project_id}/members/{engineer_employee.id}", headers=headers_admin
    )
    assert remove_member_response.status_code == 200
    assert len(remove_member_response.json()["members"]) == 1

    update_response = client.patch(
        f"/api/v1/projects/{project_id}", headers=headers_admin, json={"status": "on_hold"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "on_hold"

    list_response = client.get("/api/v1/projects", headers=headers_admin)
    assert list_response.status_code == 200
    assert any(p["id"] == project_id for p in list_response.json()["items"])

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=headers_admin)
    assert delete_response.status_code == 204

    get_after_delete = client.get(f"/api/v1/projects/{project_id}", headers=headers_admin)
    assert get_after_delete.status_code == 404


def test_creating_project_with_duplicate_name_returns_409(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    payload = {"name": "Internal Tooling", "is_billable": False}
    first = client.post("/api/v1/projects", headers=headers_admin, json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/projects", headers=headers_admin, json=payload)
    assert second.status_code == 409


def test_project_rejects_cross_tenant_client_and_member(client, tenant_a, tenant_b):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    foreign_client_id = _create_client(client, tenant_b.auth_headers(client, "Admin"), name="Foreign Client")
    _, foreign_employee, _ = tenant_b.users["Employee"]

    wrong_client_response = client.post(
        "/api/v1/projects",
        headers=headers_admin,
        json={"name": "Cross Tenant Client Test", "client_id": foreign_client_id, "is_billable": True},
    )
    assert wrong_client_response.status_code == 422

    wrong_member_response = client.post(
        "/api/v1/projects",
        headers=headers_admin,
        json={
            "name": "Cross Tenant Member Test",
            "is_billable": True,
            "member_ids": [{"employee_id": str(foreign_employee.id), "role_on_project": "member"}],
        },
    )
    assert wrong_member_response.status_code == 422


def test_employee_role_cannot_manage_projects_but_can_view_own(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer_employee, _ = tenant_a.users["Employee"]

    create_response = client.post(
        "/api/v1/projects",
        headers=headers_admin,
        json={
            "name": "My Assigned Project",
            "is_billable": True,
            "member_ids": [{"employee_id": str(engineer_employee.id), "role_on_project": "member"}],
        },
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    headers_employee = tenant_a.auth_headers(client, "Employee")

    forbidden_create = client.post(
        "/api/v1/projects", headers=headers_employee, json={"name": "Should Fail", "is_billable": True}
    )
    assert forbidden_create.status_code == 403

    forbidden_list = client.get("/api/v1/projects", headers=headers_employee)
    assert forbidden_list.status_code == 403

    my_projects_response = client.get("/api/v1/projects/mine", headers=headers_employee)
    assert my_projects_response.status_code == 200
    my_projects = my_projects_response.json()
    assert len(my_projects) == 1
    assert my_projects[0]["id"] == project_id
    assert my_projects[0]["role_on_project"] == "member"


def test_projects_and_clients_isolated_per_company(client, tenant_a, tenant_b):
    headers_a = tenant_a.auth_headers(client, "Admin")
    client.post("/api/v1/projects", headers=headers_a, json={"name": "Acme Only Project", "is_billable": True})
    _create_client(client, headers_a, name="Acme Only Client")

    headers_b = tenant_b.auth_headers(client, "Admin")
    projects_b = client.get("/api/v1/projects", headers=headers_b)
    assert projects_b.status_code == 200
    assert all(p["name"] != "Acme Only Project" for p in projects_b.json()["items"])

    clients_b = client.get("/api/v1/clients", headers=headers_b)
    assert clients_b.status_code == 200
    assert all(c["name"] != "Acme Only Client" for c in clients_b.json())


def test_manager_can_view_but_not_delete_projects(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    create_response = client.post(
        "/api/v1/projects", headers=headers_admin, json={"name": "Manager Visible Project", "is_billable": True}
    )
    project_id = create_response.json()["id"]

    headers_manager = tenant_a.auth_headers(client, "Manager")
    view_response = client.get(f"/api/v1/projects/{project_id}", headers=headers_manager)
    assert view_response.status_code == 200

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=headers_manager)
    assert delete_response.status_code == 403
