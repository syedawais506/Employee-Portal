"""Dashboard widgets (Employee.birth_date, optional PII surfaced on both
employee responses for the Birthdays/New-Hires dashboard widgets) and
location-scoped, calendar-anchored timesheet reminders.

Reminders are configured per (company, location) via TimesheetReminderRule
(location=None is the default/fallback rule, same nullable convention as
HolidayCalendar.location) — e.g. US employees get a weekly-cadence reminder,
India employees a monthly one. Cadence is calendar-anchored: "weekly" checks
whether the most recently fully-elapsed week has a submission overlapping
it, "monthly" the most recently fully-elapsed calendar month — not a rolling
"N days since last submission" count. Unlike the document-expiry digest,
which fires exactly once, this one intentionally re-fires every day the
relevant period stays uncovered (past its `grace_days`), until a submission
overlapping that period exists.

The digest task opens its own SessionLocal() (same reasoning as every other
digest check — see test_digests_and_webhooks.py's module docstring), so
these tests call `_notify_stale_timesheets` directly against the test's
`db_session` rather than the full `run_daily_digest()` task. See
docs/ROADMAP.md.
"""

from datetime import date

from sqlalchemy import select

from app.models.notification import Notification
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


def _create_rule(client, headers, *, location=None, cadence="weekly", enabled=True, grace_days=0):
    response = client.post(
        "/api/v1/timesheets/reminder-rules",
        headers=headers,
        json={"location": location, "enabled": enabled, "cadence": cadence, "grace_days": grace_days},
    )
    assert response.status_code == 201, response.text
    return response.json()


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


# -- reminder rule CRUD --------------------------------------------------------


def test_reminder_rules_empty_by_default(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    response = client.get("/api/v1/timesheets/reminder-rules", headers=headers_admin)
    assert response.status_code == 200
    assert response.json() == []


def test_admin_can_create_default_and_location_scoped_rules(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    default_rule = _create_rule(client, headers_admin, location=None, cadence="weekly", grace_days=1)
    assert default_rule["location"] is None
    india_rule = _create_rule(client, headers_admin, location="India", cadence="monthly", grace_days=2)
    assert india_rule["location"] == "India"
    assert india_rule["cadence"] == "monthly"

    listed = client.get("/api/v1/timesheets/reminder-rules", headers=headers_admin)
    assert {rule["location"] for rule in listed.json()} == {None, "India"}


def test_duplicate_location_rejected_with_409(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _create_rule(client, headers_admin, location="United States")
    response = client.post(
        "/api/v1/timesheets/reminder-rules",
        headers=headers_admin,
        json={"location": "United States", "enabled": True, "cadence": "weekly", "grace_days": 0},
    )
    assert response.status_code == 409


def test_invalid_cadence_rejected(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    response = client.post(
        "/api/v1/timesheets/reminder-rules",
        headers=headers_admin,
        json={"location": None, "enabled": True, "cadence": "daily", "grace_days": 0},
    )
    assert response.status_code == 422


def test_update_and_delete_reminder_rule(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    rule = _create_rule(client, headers_admin, location="United States", cadence="weekly", enabled=False)

    update = client.patch(
        f"/api/v1/timesheets/reminder-rules/{rule['id']}",
        headers=headers_admin,
        json={"enabled": True, "cadence": "monthly"},
    )
    assert update.status_code == 200
    assert update.json()["enabled"] is True
    assert update.json()["cadence"] == "monthly"

    delete = client.delete(f"/api/v1/timesheets/reminder-rules/{rule['id']}", headers=headers_admin)
    assert delete.status_code == 204
    assert client.get("/api/v1/timesheets/reminder-rules", headers=headers_admin).json() == []


def test_reminder_rule_mutation_gated_on_timesheet_configure(client, tenant_a):
    headers_hr = tenant_a.auth_headers(client, "HR")
    # HR holds timesheet.view (GET works) but not timesheet.configure (mutation is blocked).
    assert client.get("/api/v1/timesheets/reminder-rules", headers=headers_hr).status_code == 200
    response = client.post(
        "/api/v1/timesheets/reminder-rules",
        headers=headers_hr,
        json={"location": None, "enabled": True, "cadence": "weekly", "grace_days": 0},
    )
    assert response.status_code == 403


# -- stale-timesheet digest: calendar-anchored weekly/monthly cadence ---------


def test_no_reminder_when_no_rule_configured(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    _create_project(client, headers_admin, member_ids=[_member(engineer)])

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 15))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)


def test_no_reminder_when_rule_disabled(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    _create_project(client, headers_admin, member_ids=[_member(engineer)])
    _create_rule(client, headers_admin, location=None, cadence="weekly", enabled=False)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 15))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)


def test_weekly_cadence_fires_once_grace_period_elapses(client, tenant_a, db_session):
    """week_start_day defaults to Monday, so for 'today' values in the week of
    Mon 2026-06-15 – Sun 2026-06-21, the most recently fully-elapsed week is
    Mon 2026-06-08 – Sun 2026-06-14. With grace_days=2, nagging starts on
    2026-06-17 (the day after the week ends, plus 2 grace days).
    """
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    _create_project(client, headers_admin, member_ids=[_member(engineer)])
    _create_rule(client, headers_admin, location=None, cadence="weekly", enabled=True, grace_days=2)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 16))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 17))
    assert "timesheet.reminder" in _notification_types(client, headers_employee)


def test_reminder_repeats_daily_while_period_stays_uncovered(client, tenant_a, db_session):
    """The whole point of this feature: it must fire again the NEXT day too,
    not just once — the exact opposite of the document-expiry digest.
    """
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    _create_project(client, headers_admin, member_ids=[_member(engineer)])
    _create_rule(client, headers_admin, location=None, cadence="weekly", enabled=True, grace_days=0)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 15))
    first_count = _notification_types(client, headers_employee).count("timesheet.reminder")
    assert first_count == 1

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 16))
    second_count = _notification_types(client, headers_employee).count("timesheet.reminder")
    assert second_count == 2  # fired again the next day — not deduped


def test_reminder_stops_once_a_submission_covers_the_period(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    project_id = _create_project(client, headers_admin, member_ids=[_member(engineer)])
    _create_rule(client, headers_admin, location=None, cadence="weekly", enabled=True, grace_days=0)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 15))
    assert _notification_types(client, headers_employee).count("timesheet.reminder") == 1

    entry = client.post(
        "/api/v1/timesheets/entries",
        headers=headers_employee,
        json={"project_id": project_id, "entry_date": "2026-06-10", "hours": "4.00", "description": "Backfilled work"},
    )
    assert entry.status_code == 201, entry.text
    submission = client.post(
        "/api/v1/timesheets/submissions",
        headers=headers_employee,
        json={"period_start": "2026-06-10", "period_end": "2026-06-10"},
    )
    assert submission.status_code == 201, submission.text

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 16))
    assert _notification_types(client, headers_employee).count("timesheet.reminder") == 1  # no new one


def test_monthly_cadence_checks_calendar_month(client, tenant_a, db_session):
    """For 'today' values in early July 2026, the most recently fully-elapsed
    calendar month is June 2026. With grace_days=3, nagging starts on
    2026-07-04 (the day after June ends, plus 3 grace days).
    """
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    client.patch(f"/api/v1/employees/{engineer.id}", headers=headers_admin, json={"location": "India"})
    _create_project(client, headers_admin, member_ids=[_member(engineer)])
    _create_rule(client, headers_admin, location="India", cadence="monthly", enabled=True, grace_days=3)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 7, 3))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 7, 4))
    assert "timesheet.reminder" in _notification_types(client, headers_employee)


def test_location_specific_rule_takes_precedence_over_default(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    client.patch(f"/api/v1/employees/{engineer.id}", headers=headers_admin, json={"location": "India"})
    _create_project(client, headers_admin, member_ids=[_member(engineer)])
    # Default rule is enabled, but the more specific India rule is disabled —
    # the India-located employee should follow the India rule, not the default.
    _create_rule(client, headers_admin, location=None, cadence="weekly", enabled=True, grace_days=0)
    _create_rule(client, headers_admin, location="India", cadence="weekly", enabled=False)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 15))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)


def test_employee_whose_location_matches_no_rule_and_no_default_is_never_reminded(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _, engineer, _ = tenant_a.users["Employee"]
    client.patch(f"/api/v1/employees/{engineer.id}", headers=headers_admin, json={"location": "Germany"})
    _create_project(client, headers_admin, member_ids=[_member(engineer)])
    # Only a United States rule exists — no default (location=None) rule, and
    # this employee's location doesn't match it.
    _create_rule(client, headers_admin, location="United States", cadence="weekly", enabled=True, grace_days=0)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 15))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)


def test_employee_with_no_project_membership_is_never_reminded(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    _create_rule(client, headers_admin, location=None, cadence="weekly", enabled=True, grace_days=0)

    # No project created at all — engineer has zero project memberships.
    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 15))
    assert "timesheet.reminder" not in _notification_types(client, headers_employee)


def test_employee_not_yet_joined_during_the_period_is_skipped(client, tenant_a, db_session):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    # A brand-new hire joining mid-way through the last-completed week under
    # test (2026-06-08 – 2026-06-14) — the period before their joining_date
    # isn't theirs to have submitted for, so it's skipped entirely rather
    # than counted as an uncovered/stale period.
    create = client.post(
        "/api/v1/employees",
        headers=headers_admin,
        json={
            "email": "newhire@acme-demo.com",
            "first_name": "New",
            "last_name": "Hire",
            "employment_type": "full_time",
            "joining_date": "2026-06-20",
        },
    )
    assert create.status_code == 201, create.text
    new_hire = create.json()

    _create_project(client, headers_admin, member_ids=[{"employee_id": new_hire["id"], "role_on_project": "member"}])
    _create_rule(client, headers_admin, location=None, cadence="weekly", enabled=True, grace_days=0)

    digest_tasks_module._notify_stale_timesheets(db_session, tenant_a.company.id, date(2026, 6, 15))

    # The new hire's account is still deactivated pending onboarding, so there's
    # no login to check notifications through the API — query directly instead.
    notified_types = db_session.execute(
        select(Notification.type).where(Notification.company_id == tenant_a.company.id)
    ).scalars().all()
    assert "timesheet.reminder" not in notified_types
