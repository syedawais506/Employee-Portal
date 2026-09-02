"""Timesheets (Phase 4): entries, period submission, the simplified
Manager(+optional Finance) approval chain, the rule engine, locking/reopen,
bulk approve, dashboard/export gating, and tenant isolation. See docs/ROADMAP.md.
"""

from datetime import date, timedelta

MONDAY = date(2026, 6, 1)  # a fixed Monday so week-boundary math is deterministic in tests
WEEK_END = MONDAY + timedelta(days=6)


def _set_manager(client, headers_admin, employee_id, manager_id):
    response = client.patch(
        f"/api/v1/employees/{employee_id}", headers=headers_admin, json={"manager_id": str(manager_id)}
    )
    assert response.status_code == 200, response.text


def _member(employee, role="member"):
    return {"employee_id": str(employee.id), "role_on_project": role}


def _create_project(client, headers, *, name="Website Revamp", member_ids=None):
    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": name, "is_billable": True, "member_ids": member_ids or []},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_entry(client, headers, *, project_id, entry_date, hours, description="Work done"):
    return client.post(
        "/api/v1/timesheets/entries",
        headers=headers,
        json={"project_id": project_id, "entry_date": str(entry_date), "hours": hours, "description": description},
    )


def _submit(client, headers, period_start=MONDAY, period_end=WEEK_END):
    return client.post(
        "/api/v1/timesheets/submissions",
        headers=headers,
        json={"period_start": str(period_start), "period_end": str(period_end)},
    )


def test_full_lifecycle_entry_submit_approve_locks_entries(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, manager, _ = tenant_a.users["Manager"]
    _set_manager(client, headers_admin, engineer.id, manager.id)

    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    create_response = _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["status"] == "draft"

    submit_response = _submit(client, headers_employee)
    assert submit_response.status_code == 201, submit_response.text
    submission = submit_response.json()
    assert submission["status"] == "submitted"
    entry_id = submission["entries"][0]["id"]

    approve_url = f"/api/v1/timesheets/submissions/{submission['id']}/approve"
    approve_response = client.post(approve_url, headers=headers_manager)
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    locked_edit = client.patch(
        f"/api/v1/timesheets/entries/{entry_id}", headers=headers_employee, json={"hours": "5.00"}
    )
    assert locked_edit.status_code == 409

    # The approved submission's range spans the whole week (Monday..Sunday),
    # but only Monday actually has an entry. Logging a fresh entry on a
    # different, never-submitted day in that same range must still work —
    # locking is per-entry, not a blanket freeze over the whole date range.
    other_day = _create_entry(
        client, headers_employee, project_id=project_id, entry_date=WEEK_END, hours="2.00"
    )
    assert other_day.status_code == 201, other_day.text


def test_duplicate_entry_same_date_and_project_returns_409(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    first = _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="3.00")
    assert first.status_code == 201
    second = _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="2.00")
    assert second.status_code == 409


def test_entry_rejects_project_employee_is_not_a_member_of(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    project_id = _create_project(client, headers_admin, name="Not My Project")

    response = _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="3.00")
    assert response.status_code == 422


def test_max_hours_per_day_rule_enforced(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    config_response = client.patch(
        "/api/v1/timesheets/config", headers=headers_admin, json={"max_hours_per_day": "8.00"}
    )
    assert config_response.status_code == 200

    within_limit = _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="8.00")
    assert within_limit.status_code == 201

    project_id_2 = _create_project(client, headers_admin, name="Second Project", member_ids=[_member(engineer)])
    over_limit = _create_entry(client, headers_employee, project_id=project_id_2, entry_date=MONDAY, hours="1.00")
    assert over_limit.status_code == 422


def test_reject_then_resubmit_flow(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, manager, _ = tenant_a.users["Manager"]
    _set_manager(client, headers_admin, engineer.id, manager.id)
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    submission = _submit(client, headers_employee).json()

    reject_response = client.post(
        f"/api/v1/timesheets/submissions/{submission['id']}/reject",
        headers=headers_manager,
        json={"reason": "Please add more detail"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"

    entry_id = submission["entries"][0]["id"]
    edit_response = client.patch(
        f"/api/v1/timesheets/entries/{entry_id}", headers=headers_employee, json={"description": "More detail added"}
    )
    assert edit_response.status_code == 200

    resubmit_response = _submit(client, headers_employee)
    assert resubmit_response.status_code == 201
    assert resubmit_response.json()["status"] == "submitted"
    assert resubmit_response.json()["id"] == submission["id"]

    approve_url = f"/api/v1/timesheets/submissions/{submission['id']}/approve"
    approve_response = client.post(approve_url, headers=headers_manager)
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"


def test_finance_approval_step_when_company_requires_it(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_finance = tenant_a.auth_headers(client, "Finance")
    _, manager, _ = tenant_a.users["Manager"]
    _set_manager(client, headers_admin, engineer.id, manager.id)
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    config_response = client.patch(
        "/api/v1/timesheets/config", headers=headers_admin, json={"require_finance_approval": True}
    )
    assert config_response.status_code == 200

    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    submission = _submit(client, headers_employee).json()
    approve_url = f"/api/v1/timesheets/submissions/{submission['id']}/approve"

    manager_approve = client.post(approve_url, headers=headers_manager)
    assert manager_approve.status_code == 200
    assert manager_approve.json()["status"] == "manager_approved"

    finance_approve = client.post(approve_url, headers=headers_finance)
    assert finance_approve.status_code == 200
    assert finance_approve.json()["status"] == "approved"


def test_bulk_approve_reports_partial_failures(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    submission = _submit(client, headers_employee).json()

    bogus_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(
        "/api/v1/timesheets/submissions/bulk-approve",
        headers=headers_admin,
        json={"submission_ids": [submission["id"], bogus_id]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["approved"] == [submission["id"]]
    assert len(body["failed"]) == 1
    assert body["failed"][0]["id"] == bogus_id


def test_reopen_is_admin_only(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, manager, _ = tenant_a.users["Manager"]
    _set_manager(client, headers_admin, engineer.id, manager.id)
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    submission = _submit(client, headers_employee).json()
    approve_url = f"/api/v1/timesheets/submissions/{submission['id']}/approve"
    client.post(approve_url, headers=headers_manager)

    reopen_url = f"/api/v1/timesheets/submissions/{submission['id']}/reopen"
    manager_reopen = client.post(reopen_url, headers=headers_manager)
    assert manager_reopen.status_code == 403

    admin_reopen = client.post(reopen_url, headers=headers_admin)
    assert admin_reopen.status_code == 200
    assert admin_reopen.json()["status"] == "submitted"


def test_dashboard_and_export_are_not_visible_to_plain_employees(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_admin = tenant_a.auth_headers(client, "Admin")

    assert client.get("/api/v1/timesheets/dashboard", headers=headers_employee).status_code == 403
    assert client.get("/api/v1/timesheets/dashboard", headers=headers_manager).status_code == 200

    assert client.get("/api/v1/timesheets/export", headers=headers_employee).status_code == 403
    assert client.get("/api/v1/timesheets/export", headers=headers_admin).status_code == 200


def test_timesheet_submissions_isolated_per_company(client, tenant_a, tenant_b):
    headers_admin_a = tenant_a.auth_headers(client, "Admin")
    _, engineer_a, _ = tenant_a.users["Employee"]
    headers_employee_a = tenant_a.auth_headers(client, "Employee")
    project_id_a = _create_project(client, headers_admin_a, member_ids=[_member(engineer_a)])
    _create_entry(client, headers_employee_a, project_id=project_id_a, entry_date=MONDAY, hours="4.00")
    _submit(client, headers_employee_a)

    headers_manager_a = tenant_a.auth_headers(client, "Manager")
    submissions_a = client.get("/api/v1/timesheets/submissions", headers=headers_manager_a)
    assert submissions_a.json()["total"] == 1

    headers_manager_b = tenant_b.auth_headers(client, "Manager")
    submissions_b = client.get("/api/v1/timesheets/submissions", headers=headers_manager_b)
    assert submissions_b.status_code == 200
    assert submissions_b.json()["total"] == 0


def test_project_with_logged_hours_cannot_be_hard_deleted(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])
    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=headers_admin)
    assert delete_response.status_code == 409


def test_export_can_be_filtered_by_employee_location(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    _, manager, _ = tenant_a.users["Manager"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")

    india_update = client.patch(
        f"/api/v1/employees/{engineer.id}", headers=headers_admin, json={"location": "India"}
    )
    assert india_update.status_code == 200
    us_update = client.patch(
        f"/api/v1/employees/{manager.id}", headers=headers_admin, json={"location": "United States"}
    )
    assert us_update.status_code == 200

    project_id = _create_project(
        client, headers_admin, member_ids=[_member(engineer), _member(manager, "manager")]
    )
    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    _create_entry(client, headers_manager, project_id=project_id, entry_date=MONDAY, hours="3.00")

    india_export = client.get("/api/v1/timesheets/export", headers=headers_admin, params={"location": "India"})
    assert india_export.status_code == 200
    assert "Employee User" in india_export.text
    assert "Manager User" not in india_export.text

    us_export = client.get("/api/v1/timesheets/export", headers=headers_admin, params={"location": "United States"})
    assert "Manager User" in us_export.text
    assert "Employee User" not in us_export.text


def test_free_form_ranges_can_be_submitted_independently(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    later_day = MONDAY + timedelta(days=2)
    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    _create_entry(client, headers_employee, project_id=project_id, entry_date=later_day, hours="5.00")

    first_submit = _submit(client, headers_employee, period_start=MONDAY, period_end=MONDAY)
    assert first_submit.status_code == 201, first_submit.text
    assert len(first_submit.json()["entries"]) == 1

    second_submit = _submit(client, headers_employee, period_start=later_day, period_end=later_day)
    assert second_submit.status_code == 201, second_submit.text
    assert len(second_submit.json()["entries"]) == 1
    assert second_submit.json()["id"] != first_submit.json()["id"]


def test_rejected_entry_is_picked_up_by_a_different_resubmit_range(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, manager, _ = tenant_a.users["Manager"]
    _set_manager(client, headers_admin, engineer.id, manager.id)
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    submission = _submit(client, headers_employee, period_start=MONDAY, period_end=MONDAY).json()
    client.post(
        f"/api/v1/timesheets/submissions/{submission['id']}/reject",
        headers=headers_manager,
        json={"reason": "Needs detail"},
    )

    # A brand new, wider range (not the exact rejected tuple) should still sweep up the rejected entry.
    resubmit = _submit(client, headers_employee, period_start=MONDAY, period_end=WEEK_END)
    assert resubmit.status_code == 201, resubmit.text
    assert resubmit.json()["id"] != submission["id"]
    assert len(resubmit.json()["entries"]) == 1
    assert resubmit.json()["entries"][0]["status"] == "submitted"


def test_my_submissions_bucket_filtering(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, manager, _ = tenant_a.users["Manager"]
    _set_manager(client, headers_admin, engineer.id, manager.id)
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    submission = _submit(client, headers_employee, period_start=MONDAY, period_end=MONDAY).json()
    client.post(f"/api/v1/timesheets/submissions/{submission['id']}/approve", headers=headers_manager)

    mine_url = "/api/v1/timesheets/submissions/mine"
    pending = client.get(mine_url, headers=headers_employee, params={"bucket": "pending"})
    approved = client.get(mine_url, headers=headers_employee, params={"bucket": "approved"})
    rejected = client.get(mine_url, headers=headers_employee, params={"bucket": "rejected"})

    assert pending.json() == []
    assert len(approved.json()) == 1
    assert rejected.json() == []

    queue_approved = client.get(
        "/api/v1/timesheets/submissions", headers=headers_manager, params={"bucket": "approved"}
    )
    assert queue_approved.json()["total"] == 1
    queue_pending = client.get(
        "/api/v1/timesheets/submissions", headers=headers_manager, params={"bucket": "pending"}
    )
    assert queue_pending.json()["total"] == 0


def test_manager_step_is_restricted_to_the_employees_assigned_manager(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_finance = tenant_a.auth_headers(client, "Finance")
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    _create_entry(client, headers_employee, project_id=project_id, entry_date=MONDAY, hours="4.00")
    submission = _submit(client, headers_employee).json()
    approve_url = f"/api/v1/timesheets/submissions/{submission['id']}/approve"

    # No manager_id assigned yet — a Manager-role user who isn't this
    # specific employee's manager can't approve, even though they hold
    # timesheet.approve broadly.
    assert client.post(approve_url, headers=headers_manager).status_code == 403

    # Finance holds timesheet.approve too (unlike leave), so this exercises
    # the service-layer hierarchy check specifically, not just the endpoint gate.
    assert client.post(approve_url, headers=headers_finance).status_code == 403

    # Admin retains an override regardless of manager_id.
    admin_override = client.post(approve_url, headers=headers_admin)
    assert admin_override.status_code == 200
    assert admin_override.json()["status"] == "approved"


def test_a_managers_own_timesheet_routes_to_their_own_manager(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, manager, _ = tenant_a.users["Manager"]
    _, admin_employee, _ = tenant_a.users["Admin"]
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_finance = tenant_a.auth_headers(client, "Finance")
    _set_manager(client, headers_admin, manager.id, admin_employee.id)
    project_id = _create_project(client, headers_admin, member_ids=[_member(manager)])

    _create_entry(client, headers_manager, project_id=project_id, entry_date=MONDAY, hours="4.00")
    submission = _submit(client, headers_manager).json()
    approve_url = f"/api/v1/timesheets/submissions/{submission['id']}/approve"

    assert client.post(approve_url, headers=headers_finance).status_code == 403

    approved = client.post(approve_url, headers=headers_admin)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
