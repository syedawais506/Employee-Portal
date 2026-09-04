"""Role assignment: an Admin can change which role(s) an *existing* employee
holds (e.g. grant the Admin role to a specific employee) via
PUT /employees/{id}/roles — previously role_ids was only accepted at
creation time, with no way to reassign roles afterward. Gated on
`role.update` (Admin-only by default) rather than `employee.update`
(also held by HR), since granting Admin rights is a materially more
sensitive action than editing a phone number. See docs/ROADMAP.md.
"""


def test_admin_can_grant_admin_role_to_an_existing_employee(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    admin_role = tenant_a.roles["Admin"]
    employee_role = tenant_a.roles["Employee"]

    response = client.put(
        f"/api/v1/employees/{engineer.id}/roles",
        headers=headers_admin,
        json={"role_ids": [str(admin_role.id), str(employee_role.id)]},
    )
    assert response.status_code == 200, response.text
    role_names = {role["name"] for role in response.json()["roles"]}
    assert role_names == {"Admin", "Employee"}

    # The employee now genuinely has Admin permissions — confirmed by
    # logging in as them and hitting an Admin-only endpoint.
    login = client.post("/api/v1/auth/login", json={"email": engineer.email, "password": "Password@123"})
    assert login.status_code == 200
    new_admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/roles", headers=new_admin_headers).status_code == 200


def test_get_employee_reflects_current_roles(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]

    initial = client.get(f"/api/v1/employees/{engineer.id}", headers=headers_admin)
    assert initial.status_code == 200
    assert [role["name"] for role in initial.json()["roles"]] == ["Employee"]


def test_hr_cannot_reassign_roles_despite_holding_employee_update(client, tenant_a):
    headers_hr = tenant_a.auth_headers(client, "HR")
    _, engineer, _ = tenant_a.users["Employee"]
    admin_role = tenant_a.roles["Admin"]

    response = client.put(
        f"/api/v1/employees/{engineer.id}/roles", headers=headers_hr, json={"role_ids": [str(admin_role.id)]}
    )
    assert response.status_code == 403


def test_manager_and_employee_cannot_reassign_roles(client, tenant_a):
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    employee_role = tenant_a.roles["Employee"]

    assert client.put(
        f"/api/v1/employees/{engineer.id}/roles", headers=headers_manager, json={"role_ids": [str(employee_role.id)]}
    ).status_code == 403
    assert client.put(
        f"/api/v1/employees/{engineer.id}/roles", headers=headers_employee, json={"role_ids": [str(employee_role.id)]}
    ).status_code == 403


def test_role_ids_from_another_company_are_rejected(client, tenant_a, tenant_b):
    headers_admin_a = tenant_a.auth_headers(client, "Admin")
    _, engineer_a, _ = tenant_a.users["Employee"]
    foreign_admin_role = tenant_b.roles["Admin"]

    response = client.put(
        f"/api/v1/employees/{engineer_a.id}/roles",
        headers=headers_admin_a,
        json={"role_ids": [str(foreign_admin_role.id)]},
    )
    assert response.status_code == 422


def test_cannot_remove_the_last_admin_from_the_company(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, admin_employee, _ = tenant_a.users["Admin"]
    employee_role = tenant_a.roles["Employee"]

    # tenant_a's fixture creates exactly one Admin-role user — attempting to
    # strip it from them (the only Admin) must be rejected, or the company
    # would have nobody left who could manage roles/companies at all.
    response = client.put(
        f"/api/v1/employees/{admin_employee.id}/roles",
        headers=headers_admin,
        json={"role_ids": [str(employee_role.id)]},
    )
    assert response.status_code == 422


def test_can_reassign_admin_role_when_another_admin_remains(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    _, admin_employee, _ = tenant_a.users["Admin"]
    admin_role = tenant_a.roles["Admin"]
    employee_role = tenant_a.roles["Employee"]

    # Promote Engineer to Admin first, so there are now two Admins.
    promote = client.put(
        f"/api/v1/employees/{engineer.id}/roles", headers=headers_admin, json={"role_ids": [str(admin_role.id)]}
    )
    assert promote.status_code == 200

    # Now demoting the original Admin is fine, since Engineer still holds Admin.
    demote = client.put(
        f"/api/v1/employees/{admin_employee.id}/roles",
        headers=headers_admin,
        json={"role_ids": [str(employee_role.id)]},
    )
    assert demote.status_code == 200
    assert [role["name"] for role in demote.json()["roles"]] == ["Employee"]
