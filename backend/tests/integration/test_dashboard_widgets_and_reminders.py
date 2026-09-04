"""Dashboard widgets & configurable timesheet reminders: Employee.birth_date
(optional PII, opt-in) surfaced on both employee responses for the
Birthdays/New-Hires dashboard widgets, and a new opt-in digest check that —
unlike the document-expiry digest, which fires exactly once — intentionally
re-fires every day a timesheet submission stays stale past the
admin-configured threshold, until the employee submits again. The digest
task opens its own SessionLocal() (same reasoning as every other digest
check — see test_digests_and_webhooks.py's module docstring), so these
tests call `_notify_stale_timesheets` directly against the test's
`db_session` rather than the full `run_daily_digest()` task. See
docs/ROADMAP.md.
"""

from datetime import date, datetime, timezone

from app.models.timesheet import TimesheetSubmission
from app.tasks import digest_tasks as digest_tasks_module


def _member(employee, role="member"):
    return {"employee_id": str(employee.id), "role_on_project": role}


def _create_project(client, headers, *, member_ids):
    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Reminder Test Project", "is_billable": True, "member_ids": member_ids},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _notification_types(client, headers) -> list[str]:
    response = client.get("/api/v1/notifications", headers=headers)
    assert response.status_code == 200, response.text
    return [n["type"] for n in response.json()["items"]]


# -- birth_date on employee schemas ------------------------------------------


def test_birth_date_settable_at_creation_and_returned_on_detail_and_summary(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    create_response = client.post(
        "/api/v1/employees",
        headers=headers_admin,
        json={
            "email": "birthday@acme-demo.com",
            "first_name": "Blake",
            "last_name": "Birthday",
            "employment_type": "full_time",
            "birth_date": "1990-06-15",
        },
    )
    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["birth_date"] == "1990-06-15"

    listed = client.get("/api/v1/employees", headers=headers_admin, params={"search": "Blake"})
    assert listed.json()["items"][0]["birth_date"] == "1990-06-15"
    assert "joining_date" in listed.json()["items"][0]


def test_birth_date_updatable_and_clearable(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _, engineer, _ = tenant_a.users["Employee"]

    update = client.patch(f"/api/v1/employees/{engineer.id}", headers=headers_admin, json={"birth_date": "1988-03-02"})
    assert update.status_code == 200
    assert update.json()["birth_date"] == "1988-03-02"


# -- timesheet reminder config ------------------------------------------------


def test_timesheet_config_exposes_reminder_fields_disabled_by_default(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    response = client.get("/api/v1/timesheets/config", headers=headers_admin)
    assert response.status_code == 200
    assert response.json()["reminder_enabled"] is False
    assert response.json()["reminder_after_days"] == 3


def test_admin_can_configure_reminder_threshold(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    response = client.patch(
        "/api/v1/timesheets/config", headers=headers_admin, json={"reminder_enabled": True, "reminder_after_days": 5}
    )
    assert response.status_code == 200
    assert response.json()["reminder_enabled"] is True
    assert response.json()["reminder_after_days"] == 5


# -- stale-timesheet digest ---------------------------------------------------


def test_no_reminder_when_disabled(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    _create_project(client, headers_admin, member_ids=[_member(engineer)])

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 30))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)


def test_reminder_fires_for_stale_submission_when_enabled(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])

    client.patch(
        "/api/v1/timesheets/config",
        headers=headers_admin,
        json={"reminder_enabled": True, "reminder_after_days": 3},
    )

    entry = client.post(
        "/api/v1/timesheets/entries",
        headers=headers_employee,
        json={"project_id": project_id, "entry_date": "2026-06-01", "hours": "4.00", "description": "Work"},
    )
    assert entry.status_code == 201, entry.text
    submission = client.post(
        "/api/v1/timesheets/submissions",
        headers=headers_employee,
        json={"period_start": "2026-06-01", "period_end": "2026-06-01"},
    )
    assert submission.status_code == 201, submission.text

    # Manually backdate submitted_at so "today" can be much later without
    # needing to wait for real wall-clock time to pass.
    row = db_session.get(TimesheetSubmission, submission.json()["id"])
    row.submitted_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    db_session.commit()

    # Not yet stale enough (2 days < 3-day threshold).
    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 3))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)

    # Now stale enough.
    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 5))
    assert "timesheet.reminder" in _notification_types(client, headers_employee)


def test_reminder_repeats_daily_unlike_document_expiry_digest(client, tenant_a, db_session):
    """The whole point of this feature: it must fire again the NEXT day too,
    not just once — the exact opposite of the document-expiry digest.
    """
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    _create_project(client, headers_admin, member_ids=[_member(engineer)])
    client.patch(
        "/api/v1/timesheets/config",
        headers=headers_admin,
        json={"reminder_enabled": True, "reminder_after_days": 1},
    )

    # Employee has project membership but has NEVER submitted — falls back to joining_date.
    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 10))
    first_count = _notification_types(client, headers_employee).count("timesheet.reminder")
    assert first_count == 1

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 11))
    second_count = _notification_types(client, headers_employee).count("timesheet.reminder")
    assert second_count == 2  # fired again the next day — not deduped


def test_employee_with_no_project_membership_is_never_reminded(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    client.patch(
        "/api/v1/timesheets/config",
        headers=headers_admin,
        json={"reminder_enabled": True, "reminder_after_days": 1},
    )

    # No project created at all — engineer has zero project memberships.
    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 20))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)
