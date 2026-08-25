"""Leave Management (Phase 5): leave types/holidays/settings, ledger-based
balance enforcement, overlap prevention, the on-behalf-of filing pattern
(gated on leave.approve — not the broad leave.view — per the offer-letter
permission-scoping lesson), the simplified Manager(+optional HR) approval
chain, carry-forward, and dashboard/export gating. See docs/ROADMAP.md.
"""

from datetime import date, timedelta

MONDAY = date(2026, 6, 1)  # a fixed Monday so business-day math is deterministic in tests
TUESDAY = MONDAY + timedelta(days=1)
WEDNESDAY = MONDAY + timedelta(days=2)


def _create_leave_type(client, headers, *, name="Annual Leave", annual_quota_days=20, requires_attachment=False):
    response = client.post(
        "/api/v1/leave-types",
        headers=headers,
        json={
            "name": name,
            "is_paid": True,
            "annual_quota_days": annual_quota_days,
            "max_carry_forward_days": 5,
            "requires_attachment": requires_attachment,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_request(
    client, headers, *, leave_type_id, start_date, end_date, reason=None, employee_id=None, file_content=None
):
    data = {"leave_type_id": str(leave_type_id), "start_date": str(start_date), "end_date": str(end_date)}
    if reason is not None:
        data["reason"] = reason
    if employee_id is not None:
        data["employee_id"] = str(employee_id)
    files = None
    if file_content is not None:
        files = {"file": ("certificate.pdf", file_content, "application/pdf")}
    return client.post("/api/v1/leave-requests", headers=headers, data=data, files=files)


def test_full_lifecycle_pending_to_approved_without_hr_signoff(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    leave_type = _create_leave_type(client, headers_admin)

    create_response = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=TUESDAY
    )
    assert create_response.status_code == 201, create_response.text
    request = create_response.json()
    assert request["status"] == "pending"
    assert request["days_count"] == 2

    approve_response = client.post(
        f"/api/v1/leave-requests/{request['id']}/approve", headers=headers_manager
    )
    assert approve_response.status_code == 200, approve_response.text
    assert approve_response.json()["status"] == "approved"


def test_two_tier_approval_chain_when_company_requires_hr_signoff(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_hr = tenant_a.auth_headers(client, "HR")
    leave_type = _create_leave_type(client, headers_admin)

    settings_response = client.patch(
        "/api/v1/leave/settings", headers=headers_admin, json={"require_hr_leave_approval": True}
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["require_hr_leave_approval"] is True

    request = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY
    ).json()
    approve_url = f"/api/v1/leave-requests/{request['id']}/approve"

    manager_approve = client.post(approve_url, headers=headers_manager)
    assert manager_approve.status_code == 200
    assert manager_approve.json()["status"] == "manager_approved"

    hr_approve = client.post(approve_url, headers=headers_hr)
    assert hr_approve.status_code == 200
    assert hr_approve.json()["status"] == "approved"


def test_balance_enforcement_rejects_request_exceeding_available_quota(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    leave_type = _create_leave_type(client, headers_admin, annual_quota_days=1)

    response = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=WEDNESDAY
    )
    assert response.status_code == 422, response.text


def test_unlimited_leave_type_skips_balance_enforcement(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    leave_type = _create_leave_type(client, headers_admin, name="Unpaid Leave", annual_quota_days=None)

    response = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=WEDNESDAY
    )
    assert response.status_code == 201, response.text


def test_overlapping_requests_for_same_employee_are_rejected(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    leave_type = _create_leave_type(client, headers_admin)

    first = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=TUESDAY
    )
    assert first.status_code == 201

    second = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=TUESDAY, end_date=WEDNESDAY
    )
    assert second.status_code == 409


def test_on_behalf_of_filing_requires_leave_approve_permission(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, engineer, _ = tenant_a.users["Employee"]
    _, manager, _ = tenant_a.users["Manager"]
    leave_type = _create_leave_type(client, headers_admin)

    on_behalf = _create_request(
        client, headers_manager, leave_type_id=leave_type["id"],
        start_date=MONDAY, end_date=MONDAY, employee_id=engineer.id,
    )
    assert on_behalf.status_code == 201, on_behalf.text
    assert on_behalf.json()["employee_id"] == str(engineer.id)

    denied = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"],
        start_date=MONDAY, end_date=MONDAY, employee_id=manager.id,
    )
    assert denied.status_code == 403


def test_queue_dashboard_and_export_are_gated_by_narrow_permissions_not_view(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_hr = tenant_a.auth_headers(client, "HR")

    # Queue and dashboard require leave.approve — Employee has bare leave.view only.
    assert client.get("/api/v1/leave-requests", headers=headers_employee).status_code == 403
    assert client.get("/api/v1/leave-requests", headers=headers_manager).status_code == 200
    assert client.get("/api/v1/leave/dashboard", headers=headers_employee).status_code == 403
    assert client.get("/api/v1/leave/dashboard", headers=headers_manager).status_code == 200

    # Export requires leave.export — Manager's defaults don't include it, HR's do.
    assert client.get("/api/v1/leave/export", headers=headers_manager).status_code == 403
    assert client.get("/api/v1/leave/export", headers=headers_admin).status_code == 200
    assert client.get("/api/v1/leave/export", headers=headers_hr).status_code == 200


def test_reject_flow_records_reason(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    leave_type = _create_leave_type(client, headers_admin)

    request = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY
    ).json()

    reject_response = client.post(
        f"/api/v1/leave-requests/{request['id']}/reject",
        headers=headers_manager,
        json={"reason": "Team is short-staffed that week"},
    )
    assert reject_response.status_code == 200, reject_response.text
    body = reject_response.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "Team is short-staffed that week"


def test_cancel_own_pending_request_and_manager_can_cancel_on_behalf(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    leave_type = _create_leave_type(client, headers_admin)

    own_request = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY
    ).json()
    cancel_response = client.post(f"/api/v1/leave-requests/{own_request['id']}/cancel", headers=headers_employee)
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    already_cancelled = client.post(f"/api/v1/leave-requests/{own_request['id']}/cancel", headers=headers_employee)
    assert already_cancelled.status_code == 409

    other_request = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=TUESDAY, end_date=TUESDAY
    ).json()
    manager_cancel = client.post(f"/api/v1/leave-requests/{other_request['id']}/cancel", headers=headers_manager)
    assert manager_cancel.status_code == 200
    assert manager_cancel.json()["status"] == "cancelled"


def test_delete_request_requires_delete_permission(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    leave_type = _create_leave_type(client, headers_admin)

    request = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY
    ).json()

    forbidden = client.delete(f"/api/v1/leave-requests/{request['id']}", headers=headers_employee)
    assert forbidden.status_code == 403

    allowed = client.delete(f"/api/v1/leave-requests/{request['id']}", headers=headers_admin)
    assert allowed.status_code == 204


def test_leave_type_in_use_cannot_be_hard_deleted(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    leave_type = _create_leave_type(client, headers_admin)
    _create_request(client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY)

    delete_response = client.delete(f"/api/v1/leave-types/{leave_type['id']}", headers=headers_admin)
    assert delete_response.status_code == 409


def test_attachment_required_when_leave_type_demands_it(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    leave_type = _create_leave_type(client, headers_admin, name="Sick Leave", requires_attachment=True)

    without_attachment = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY
    )
    assert without_attachment.status_code == 422

    with_attachment = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY,
        file_content=b"Demo medical certificate content.",
    )
    assert with_attachment.status_code == 201, with_attachment.text
    assert with_attachment.json()["attachment_original_filename"] == "certificate.pdf"


def test_carry_forward_requires_configure_permission_and_updates_next_year_balance(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_hr = tenant_a.auth_headers(client, "HR")
    leave_type = _create_leave_type(client, headers_admin, annual_quota_days=20)

    _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=TUESDAY
    )

    hr_denied = client.post(
        "/api/v1/leave/carry-forward", headers=headers_hr, json={"from_year": MONDAY.year}
    )
    assert hr_denied.status_code == 403

    admin_allowed = client.post(
        "/api/v1/leave/carry-forward", headers=headers_admin, json={"from_year": MONDAY.year}
    )
    assert admin_allowed.status_code == 200
    assert admin_allowed.json()["to_year"] == MONDAY.year + 1

    next_year_balances = client.get(
        "/api/v1/leave/balances/mine", headers=headers_employee, params={"year": MONDAY.year + 1}
    ).json()
    balance = next((b for b in next_year_balances if b["leave_type_id"] == leave_type["id"]), None)
    assert balance is not None
    # 20 granted - 2 used = 18 remaining, but capped at the leave type's max_carry_forward_days (5).
    assert balance["carried_forward"] == "5.0"


def test_leave_requests_isolated_per_company(client, tenant_a, tenant_b):
    headers_admin_a = tenant_a.auth_headers(client, "Admin")
    headers_employee_a = tenant_a.auth_headers(client, "Employee")
    leave_type_a = _create_leave_type(client, headers_admin_a)
    _create_request(client, headers_employee_a, leave_type_id=leave_type_a["id"], start_date=MONDAY, end_date=MONDAY)

    headers_manager_a = tenant_a.auth_headers(client, "Manager")
    queue_a = client.get("/api/v1/leave-requests", headers=headers_manager_a)
    assert queue_a.json()["total"] == 1

    headers_manager_b = tenant_b.auth_headers(client, "Manager")
    queue_b = client.get("/api/v1/leave-requests", headers=headers_manager_b)
    assert queue_b.status_code == 200
    assert queue_b.json()["total"] == 0


def test_export_returns_csv_with_employee_and_status(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    leave_type = _create_leave_type(client, headers_admin)

    request = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY
    ).json()
    client.post(f"/api/v1/leave-requests/{request['id']}/approve", headers=headers_manager)

    export_response = client.get("/api/v1/leave/export", headers=headers_admin)
    assert export_response.status_code == 200
    assert "Employee User" in export_response.text


def test_location_scoped_holiday_only_excludes_business_days_for_matching_employees(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, engineer, _ = tenant_a.users["Employee"]
    leave_type = _create_leave_type(client, headers_admin)

    location_update = client.patch(
        f"/api/v1/employees/{engineer.id}", headers=headers_admin, json={"location": "India"}
    )
    assert location_update.status_code == 200

    holiday_response = client.post(
        "/api/v1/holidays", headers=headers_admin, json={"date": str(TUESDAY), "name": "Diwali", "location": "India"}
    )
    assert holiday_response.status_code == 201

    india_request = _create_request(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=WEDNESDAY
    )
    assert india_request.status_code == 201
    assert india_request.json()["days_count"] == 2  # Tuesday excluded as a holiday for India

    unset_location_request = _create_request(
        client, headers_manager, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=WEDNESDAY
    )
    assert unset_location_request.status_code == 201
    # Manager has no location set, so the India-scoped holiday doesn't apply to them.
    assert unset_location_request.json()["days_count"] == 3


def test_holiday_uniqueness_is_scoped_per_location(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    company_wide = client.post(
        "/api/v1/holidays", headers=headers_admin, json={"date": str(MONDAY), "name": "Founders Day"}
    )
    assert company_wide.status_code == 201

    india_only = client.post(
        "/api/v1/holidays", headers=headers_admin, json={"date": str(MONDAY), "name": "Diwali", "location": "India"}
    )
    assert india_only.status_code == 201

    duplicate = client.post("/api/v1/holidays", headers=headers_admin, json={"date": str(MONDAY), "name": "Duplicate"})
    assert duplicate.status_code == 409


def test_holiday_location_can_be_cleared_via_update(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    created = client.post(
        "/api/v1/holidays", headers=headers_admin, json={"date": str(MONDAY), "name": "Diwali", "location": "India"}
    )
    holiday_id = created.json()["id"]

    updated = client.patch(f"/api/v1/holidays/{holiday_id}", headers=headers_admin, json={"clear_location": True})
    assert updated.status_code == 200
    assert updated.json()["location"] is None
