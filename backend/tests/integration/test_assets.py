"""Assets (Phase 6): asset types, assign/return with no approval step (Admin/HR
act directly), a ledger-based assignment history (current holder is always
derived from the open assignment row, never a stored "assigned to" field on
the asset), and the self-scoped /assets/mine endpoint that needs only
authentication — matching the same self-scoping pattern used for
/leave-requests/mine and /timesheets/entries. See docs/ROADMAP.md.
"""


def _create_asset_type(client, headers, *, name="Laptop"):
    response = client.post("/api/v1/asset-types", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def _create_asset(client, headers, *, asset_type_id, asset_tag="LT-001", name="Dell Latitude"):
    response = client.post(
        "/api/v1/assets",
        headers=headers,
        json={"asset_type_id": asset_type_id, "asset_tag": asset_tag, "name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_full_lifecycle_assign_and_return(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    asset_type = _create_asset_type(client, headers_admin)
    asset = _create_asset(client, headers_admin, asset_type_id=asset_type["id"])
    assert asset["status"] == "available"
    assert asset["current_employee_id"] is None

    assign_response = client.post(
        f"/api/v1/assets/{asset['id']}/assign", headers=headers_admin, json={"employee_id": str(engineer.id)}
    )
    assert assign_response.status_code == 200, assign_response.text
    assigned = assign_response.json()
    assert assigned["status"] == "assigned"
    assert assigned["current_employee_id"] == str(engineer.id)

    return_response = client.post(f"/api/v1/assets/{asset['id']}/return", headers=headers_admin)
    assert return_response.status_code == 200, return_response.text
    returned = return_response.json()
    assert returned["status"] == "available"
    assert returned["current_employee_id"] is None

    history_response = client.get(f"/api/v1/assets/{asset['id']}/history", headers=headers_admin)
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["employee_id"] == str(engineer.id)
    assert history[0]["returned_at"] is not None


def test_cannot_assign_an_unavailable_asset(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    _, manager, _ = tenant_a.users["Manager"]
    asset_type = _create_asset_type(client, headers_admin)
    asset = _create_asset(client, headers_admin, asset_type_id=asset_type["id"])

    client.post(f"/api/v1/assets/{asset['id']}/assign", headers=headers_admin, json={"employee_id": str(engineer.id)})

    second_assign = client.post(
        f"/api/v1/assets/{asset['id']}/assign", headers=headers_admin, json={"employee_id": str(manager.id)}
    )
    assert second_assign.status_code == 409


def test_cannot_return_an_asset_that_is_not_assigned(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    asset_type = _create_asset_type(client, headers_admin)
    asset = _create_asset(client, headers_admin, asset_type_id=asset_type["id"])

    response = client.post(f"/api/v1/assets/{asset['id']}/return", headers=headers_admin)
    assert response.status_code == 409


def test_cannot_directly_set_status_to_assigned_via_update(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    asset_type = _create_asset_type(client, headers_admin)
    asset = _create_asset(client, headers_admin, asset_type_id=asset_type["id"])

    response = client.patch(f"/api/v1/assets/{asset['id']}", headers=headers_admin, json={"status": "assigned"})
    assert response.status_code == 422


def test_duplicate_asset_tag_rejected(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    asset_type = _create_asset_type(client, headers_admin)
    _create_asset(client, headers_admin, asset_type_id=asset_type["id"], asset_tag="DUP-001")

    response = client.post(
        "/api/v1/assets",
        headers=headers_admin,
        json={"asset_type_id": asset_type["id"], "asset_tag": "DUP-001", "name": "Another Laptop"},
    )
    assert response.status_code == 409


def test_asset_with_assignment_history_cannot_be_hard_deleted(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    asset_type = _create_asset_type(client, headers_admin)
    asset = _create_asset(client, headers_admin, asset_type_id=asset_type["id"])
    client.post(f"/api/v1/assets/{asset['id']}/assign", headers=headers_admin, json={"employee_id": str(engineer.id)})

    delete_response = client.delete(f"/api/v1/assets/{asset['id']}", headers=headers_admin)
    assert delete_response.status_code == 409


def test_asset_type_in_use_cannot_be_hard_deleted(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    asset_type = _create_asset_type(client, headers_admin)
    _create_asset(client, headers_admin, asset_type_id=asset_type["id"])

    delete_response = client.delete(f"/api/v1/asset-types/{asset_type['id']}", headers=headers_admin)
    assert delete_response.status_code == 409


def test_permission_gating_across_roles(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_hr = tenant_a.auth_headers(client, "HR")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_employee = tenant_a.auth_headers(client, "Employee")

    # Employee has no asset.view at all.
    assert client.get("/api/v1/assets", headers=headers_employee).status_code == 403

    # Manager has view-only.
    assert client.get("/api/v1/assets", headers=headers_manager).status_code == 200
    manager_create = client.post("/api/v1/asset-types", headers=headers_manager, json={"name": "Phone"})
    assert manager_create.status_code == 403

    # HR can create/update/export but not delete.
    asset_type = _create_asset_type(client, headers_hr, name="Monitor")
    asset = _create_asset(client, headers_hr, asset_type_id=asset_type["id"], asset_tag="MON-001")
    hr_delete = client.delete(f"/api/v1/assets/{asset['id']}", headers=headers_hr)
    assert hr_delete.status_code == 403
    assert client.get("/api/v1/assets/export", headers=headers_hr).status_code == 200
    assert client.get("/api/v1/assets/export", headers=headers_manager).status_code == 403

    # Admin can do everything, including delete (no assignment history yet).
    admin_delete = client.delete(f"/api/v1/assets/{asset['id']}", headers=headers_admin)
    assert admin_delete.status_code == 204


def test_my_assets_is_self_scoped_and_needs_no_asset_permission(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    asset_type = _create_asset_type(client, headers_admin)
    asset = _create_asset(client, headers_admin, asset_type_id=asset_type["id"])
    client.post(f"/api/v1/assets/{asset['id']}/assign", headers=headers_admin, json={"employee_id": str(engineer.id)})

    mine_response = client.get("/api/v1/assets/mine", headers=headers_employee)
    assert mine_response.status_code == 200
    mine = mine_response.json()
    assert len(mine) == 1
    assert mine[0]["asset_tag"] == asset["asset_tag"]
    assert mine[0]["returned_at"] is None


def test_summary_counts_by_status(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    asset_type = _create_asset_type(client, headers_admin)
    _create_asset(client, headers_admin, asset_type_id=asset_type["id"], asset_tag="SUM-001")
    assigned_asset = _create_asset(client, headers_admin, asset_type_id=asset_type["id"], asset_tag="SUM-002")
    client.post(
        f"/api/v1/assets/{assigned_asset['id']}/assign", headers=headers_admin, json={"employee_id": str(engineer.id)}
    )

    summary = client.get("/api/v1/assets/summary", headers=headers_admin)
    assert summary.status_code == 200
    body = summary.json()
    assert body["total"] == 2
    assert body["available"] == 1
    assert body["assigned"] == 1


def test_assets_isolated_per_company(client, tenant_a, tenant_b):
    headers_admin_a = tenant_a.auth_headers(client, "Admin")
    asset_type_a = _create_asset_type(client, headers_admin_a)
    _create_asset(client, headers_admin_a, asset_type_id=asset_type_a["id"])

    headers_admin_b = tenant_b.auth_headers(client, "Admin")
    list_b = client.get("/api/v1/assets", headers=headers_admin_b)
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0

    types_b = client.get("/api/v1/asset-types", headers=headers_admin_b)
    assert types_b.json() == []


def test_export_returns_csv_with_current_holder(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    asset_type = _create_asset_type(client, headers_admin)
    asset = _create_asset(client, headers_admin, asset_type_id=asset_type["id"])
    client.post(f"/api/v1/assets/{asset['id']}/assign", headers=headers_admin, json={"employee_id": str(engineer.id)})

    export_response = client.get("/api/v1/assets/export", headers=headers_admin)
    assert export_response.status_code == 200
    assert "Employee User" in export_response.text
    assert "assigned" in export_response.text
