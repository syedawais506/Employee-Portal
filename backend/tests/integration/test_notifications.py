"""Notifications (Phase 7b): a persisted per-user feed created synchronously
inside the same request/transaction as the triggering action (leave/
timesheet submit+approve+reject, asset assign, onboarding submission ->
HR review queue fan-out), plus REST list/unread-count/mark-read endpoints
that are always self-scoped to the recipient. The live WebSocket push is
best-effort on top of the persisted row and isn't covered here — it needs
its own DB connection that can't see this suite's per-test transaction (see
notifications_ws.py); what's covered is that the right row goes to the
right recipient, which is the part that actually matters. See
docs/ROADMAP.md.
"""

from starlette.testclient import WebSocketDisconnect

from app.services import onboarding_service as onboarding_service_module

MONDAY = "2026-06-01"
TUESDAY = "2026-06-02"


class _CapturedInvites:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def delay(self, email: str, token: str) -> None:
        self.calls.append((email, token))


def _set_manager(client, headers_admin, employee_id, manager_id):
    response = client.patch(
        f"/api/v1/employees/{employee_id}", headers=headers_admin, json={"manager_id": str(manager_id)}
    )
    assert response.status_code == 200, response.text


def _create_leave_type(client, headers_admin, name="Annual Leave"):
    response = client.post(
        "/api/v1/leave-types",
        headers=headers_admin,
        json={
            "name": name,
            "is_paid": True,
            "annual_quota_days": 20,
            "max_carry_forward_days": 5,
            "requires_attachment": False,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _file_leave(client, headers, *, leave_type_id, start_date, end_date, employee_id=None):
    data = {"leave_type_id": leave_type_id, "start_date": start_date, "end_date": end_date}
    if employee_id is not None:
        data["employee_id"] = str(employee_id)
    return client.post("/api/v1/leave-requests", headers=headers, data=data)


def _create_project(client, headers_admin, member_ids):
    response = client.post(
        "/api/v1/projects",
        headers=headers_admin,
        json={"name": "Notification Test Project", "is_billable": True, "member_ids": member_ids},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _notification_types(client, headers) -> list[str]:
    response = client.get("/api/v1/notifications", headers=headers)
    assert response.status_code == 200, response.text
    return [n["type"] for n in response.json()["items"]]


def test_leave_submission_notifies_manager(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, engineer, _ = tenant_a.users["Employee"]
    _, manager, _ = tenant_a.users["Manager"]
    _set_manager(client, headers_admin, engineer.id, manager.id)
    leave_type = _create_leave_type(client, headers_admin)

    response = _file_leave(client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY)
    assert response.status_code == 201, response.text

    assert "leave.submitted" in _notification_types(client, headers_manager)


def test_leave_filed_on_behalf_notifies_target_employee(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    leave_type = _create_leave_type(client, headers_admin)

    response = _file_leave(
        client,
        headers_manager,
        leave_type_id=leave_type["id"],
        start_date=TUESDAY,
        end_date=TUESDAY,
        employee_id=engineer.id,
    )
    assert response.status_code == 201, response.text

    assert "leave.filed_for_you" in _notification_types(client, headers_employee)


def test_leave_approval_and_rejection_notify_requester(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, engineer, _ = tenant_a.users["Employee"]
    _, manager, _ = tenant_a.users["Manager"]
    _set_manager(client, headers_admin, engineer.id, manager.id)
    leave_type = _create_leave_type(client, headers_admin)

    approved = _file_leave(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=MONDAY, end_date=MONDAY
    ).json()
    client.post(f"/api/v1/leave-requests/{approved['id']}/approve", headers=headers_manager)

    rejected = _file_leave(
        client, headers_employee, leave_type_id=leave_type["id"], start_date=TUESDAY, end_date=TUESDAY
    ).json()
    client.post(
        f"/api/v1/leave-requests/{rejected['id']}/reject", headers=headers_manager, json={"reason": "Short-staffed"}
    )

    types = _notification_types(client, headers_employee)
    assert "leave.approved" in types
    assert "leave.rejected" in types


def test_timesheet_submission_notifies_manager_and_approval_notifies_submitter(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    _, engineer, _ = tenant_a.users["Employee"]
    _, manager, _ = tenant_a.users["Manager"]
    _set_manager(client, headers_admin, engineer.id, manager.id)
    member = {"employee_id": str(engineer.id), "role_on_project": "member"}
    project_id = _create_project(client, headers_admin, [member])

    entry = client.post(
        "/api/v1/timesheets/entries",
        headers=headers_employee,
        json={"project_id": project_id, "entry_date": MONDAY, "hours": "4.00", "description": "Work"},
    )
    assert entry.status_code == 201, entry.text

    submission = client.post(
        "/api/v1/timesheets/submissions", headers=headers_employee, json={"period_start": MONDAY, "period_end": MONDAY}
    )
    assert submission.status_code == 201, submission.text
    assert "timesheet.submitted" in _notification_types(client, headers_manager)

    approve = client.post(
        f"/api/v1/timesheets/submissions/{submission.json()['id']}/approve", headers=headers_manager
    )
    assert approve.status_code == 200
    assert "timesheet.approved" in _notification_types(client, headers_employee)


def test_asset_assignment_notifies_employee(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]

    asset_type = client.post("/api/v1/asset-types", headers=headers_admin, json={"name": "Laptop"}).json()
    asset_payload = {"asset_type_id": asset_type["id"], "asset_tag": "NB-001", "name": "Laptop"}
    asset = client.post("/api/v1/assets", headers=headers_admin, json=asset_payload).json()

    assign = client.post(
        f"/api/v1/assets/{asset['id']}/assign", headers=headers_admin, json={"employee_id": str(engineer.id)}
    )
    assert assign.status_code == 200, assign.text
    assert "asset.assigned" in _notification_types(client, headers_employee)


def test_onboarding_submission_notifies_hr_reviewers(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_hr = tenant_a.auth_headers(client, "HR")

    doc_type_payload = {"name": "Resume", "is_required": True, "sort_order": 1}
    doc_type = client.post("/api/v1/document-types", headers=headers_admin, json=doc_type_payload).json()

    captured = _CapturedInvites()
    monkeypatch.setattr(onboarding_service_module, "send_onboarding_invite_email", captured)
    employee_payload = {
        "email": "notify-newhire@acme-demo.com",
        "first_name": "New",
        "last_name": "Hire",
        "employment_type": "full_time",
    }
    create_response = client.post("/api/v1/employees", headers=headers_admin, json=employee_payload)
    assert create_response.status_code == 201, create_response.text
    _, raw_token = captured.calls[-1]

    client.post(f"/api/v1/onboarding/{raw_token}/password", json={"password": "NewHirePass1"})
    upload = client.post(
        f"/api/v1/onboarding/{raw_token}/documents",
        data={"document_type_id": doc_type["id"]},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    assert "onboarding.submitted" in _notification_types(client, headers_hr)


def test_list_unread_only_and_pagination(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    leave_type = _create_leave_type(client, headers_admin)

    # Filed on behalf of the Employee twice, so their own feed gets two
    # "leave.filed_for_you" notifications to filter/paginate over.
    for day in (MONDAY, TUESDAY):
        response = _file_leave(
            client,
            headers_manager,
            leave_type_id=leave_type["id"],
            start_date=day,
            end_date=day,
            employee_id=engineer.id,
        )
        assert response.status_code == 201, response.text

    unread_only = client.get("/api/v1/notifications", headers=headers_employee, params={"unread_only": True})
    assert unread_only.status_code == 200
    assert unread_only.json()["total"] == 2

    paginated = client.get("/api/v1/notifications", headers=headers_employee, params={"page": 1, "page_size": 1})
    assert paginated.status_code == 200
    assert len(paginated.json()["items"]) == 1
    assert paginated.json()["total"] == 2


def test_unread_count_and_mark_read_and_mark_all_read(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    leave_type = _create_leave_type(client, headers_admin)

    for day in (MONDAY, TUESDAY):
        response = _file_leave(
            client,
            headers_manager,
            leave_type_id=leave_type["id"],
            start_date=day,
            end_date=day,
            employee_id=engineer.id,
        )
        assert response.status_code == 201, response.text

    count_response = client.get("/api/v1/notifications/unread-count", headers=headers_employee)
    assert count_response.status_code == 200
    assert count_response.json()["unread_count"] == 2

    first_id = client.get("/api/v1/notifications", headers=headers_employee).json()["items"][0]["id"]
    mark_one = client.post(f"/api/v1/notifications/{first_id}/read", headers=headers_employee)
    assert mark_one.status_code == 200
    assert mark_one.json()["is_read"] is True

    mark_all = client.post("/api/v1/notifications/read-all", headers=headers_employee)
    assert mark_all.status_code == 200
    assert mark_all.json()["marked_read"] == 1

    final_count = client.get("/api/v1/notifications/unread-count", headers=headers_employee)
    assert final_count.json()["unread_count"] == 0


def test_mark_read_is_self_scoped(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    leave_type = _create_leave_type(client, headers_admin)

    _file_leave(
        client,
        headers_manager,
        leave_type_id=leave_type["id"],
        start_date=MONDAY,
        end_date=MONDAY,
        employee_id=engineer.id,
    )
    notification_id = client.get("/api/v1/notifications", headers=headers_employee).json()["items"][0]["id"]

    other_user_attempt = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers_manager)
    assert other_user_attempt.status_code == 404


def test_notifications_isolated_per_company(client, tenant_a, tenant_b):
    headers_admin_a = tenant_a.auth_headers(client, "Admin")
    headers_manager_a = tenant_a.auth_headers(client, "Manager")
    _, engineer_a, _ = tenant_a.users["Employee"]
    leave_type = _create_leave_type(client, headers_admin_a)
    _file_leave(
        client,
        headers_manager_a,
        leave_type_id=leave_type["id"],
        start_date=MONDAY,
        end_date=MONDAY,
        employee_id=engineer_a.id,
    )

    headers_employee_b = tenant_b.auth_headers(client, "Employee")
    cross_tenant = client.get("/api/v1/notifications", headers=headers_employee_b)
    assert cross_tenant.status_code == 200
    assert cross_tenant.json()["total"] == 0


def test_ws_rejects_invalid_token(client):
    try:
        with client.websocket_connect("/api/v1/notifications/ws?token=not-a-real-token"):
            pass
        raised = False
    except WebSocketDisconnect:
        raised = True
    assert raised
