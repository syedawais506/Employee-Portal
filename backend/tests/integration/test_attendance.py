"""Attendance (Phase 9a): self-service check-in/check-out (always the caller's
own employee record, no on-behalf-of concept, so no permission catalog entry
is needed for it — the same self-scoping pattern as /leave-requests/mine),
company-wide view/export/configure gated on a new `attendance` permission
module, and a Today dashboard that enumerates every active employee (not just
those with a row) so "not checked in yet" is visible too.

Late/overtime computation depends on comparing real wall-clock time against a
configured shift, which real test-run time can't control — so those specific
tests call attendance_service.check_in/check_out directly with an explicit
`now`, the same testable-seam pattern Phase 7c's digest task used for `today`.
See docs/ROADMAP.md.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from app.services.attendance_service import attendance_service


def test_check_in_then_check_out_happy_path(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")

    check_in = client.post("/api/v1/attendance/check-in", headers=headers_employee)
    assert check_in.status_code == 201, check_in.text
    assert check_in.json()["status"] == "checked_in"
    assert check_in.json()["check_out_at"] is None

    check_out = client.post("/api/v1/attendance/check-out", headers=headers_employee)
    assert check_out.status_code == 200, check_out.text
    assert check_out.json()["status"] == "checked_out"
    assert check_out.json()["check_out_at"] is not None


def test_cannot_check_in_twice_same_day(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    client.post("/api/v1/attendance/check-in", headers=headers_employee)

    second = client.post("/api/v1/attendance/check-in", headers=headers_employee)
    assert second.status_code == 409


def test_cannot_check_out_without_checking_in(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.post("/api/v1/attendance/check-out", headers=headers_employee)
    assert response.status_code == 409


def test_cannot_check_out_twice(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    client.post("/api/v1/attendance/check-in", headers=headers_employee)
    client.post("/api/v1/attendance/check-out", headers=headers_employee)

    second = client.post("/api/v1/attendance/check-out", headers=headers_employee)
    assert second.status_code == 409


def test_mine_lists_own_records_only(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    headers_manager = tenant_a.auth_headers(client, "Manager")
    client.post("/api/v1/attendance/check-in", headers=headers_employee)
    client.post("/api/v1/attendance/check-in", headers=headers_manager)

    today = date.today().isoformat()
    response = client.get(
        "/api/v1/attendance/mine", headers=headers_employee, params={"date_from": today, "date_to": today}
    )
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["status"] == "checked_in"


def test_company_wide_view_requires_permission(client, tenant_a):
    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.get("/api/v1/attendance", headers=headers_employee)
    assert response.status_code == 403


def test_manager_can_view_company_wide_but_not_configure(client, tenant_a):
    headers_manager = tenant_a.auth_headers(client, "Manager")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    client.post("/api/v1/attendance/check-in", headers=headers_employee)

    view = client.get("/api/v1/attendance", headers=headers_manager)
    assert view.status_code == 200
    assert view.json()["total"] == 1

    configure = client.patch(
        "/api/v1/attendance/settings", headers=headers_manager, json={"grace_period_minutes": 30}
    )
    assert configure.status_code == 403


def test_admin_can_configure_shift_settings(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")

    defaults = client.get("/api/v1/attendance/settings", headers=headers_admin)
    assert defaults.status_code == 200
    assert defaults.json()["grace_period_minutes"] == 15

    updated = client.patch(
        "/api/v1/attendance/settings",
        headers=headers_admin,
        json={"grace_period_minutes": 30, "shift_start": "10:00:00"},
    )
    assert updated.status_code == 200
    assert updated.json()["grace_period_minutes"] == 30
    assert updated.json()["shift_start"] == "10:00:00"


def test_today_dashboard_distinguishes_checked_in_and_not_checked_in(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    client.post("/api/v1/attendance/check-in", headers=headers_employee)

    response = client.get("/api/v1/attendance/today", headers=headers_admin)
    assert response.status_code == 200
    by_status = {entry["status"] for entry in response.json()}
    assert "checked_in" in by_status
    assert "not_checked_in" in by_status


def test_export_requires_export_permission(client, tenant_a):
    headers_manager = tenant_a.auth_headers(client, "Manager")
    response = client.get("/api/v1/attendance/export", headers=headers_manager)
    assert response.status_code == 403

    headers_hr = tenant_a.auth_headers(client, "HR")
    response = client.get("/api/v1/attendance/export", headers=headers_hr)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]


def test_reports_hub_can_run_attendance_module(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    headers_employee = tenant_a.auth_headers(client, "Employee")
    client.post("/api/v1/attendance/check-in", headers=headers_employee)

    response = client.post(
        "/api/v1/reports/preview", headers=headers_admin, json={"module": "attendance", "filters": {}}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["header"][0] == "Employee"


def test_check_in_marks_late_after_grace_period(db_session, tenant_a):
    _, engineer, _ = tenant_a.users["Employee"]
    late_check_in = datetime(2026, 6, 15, 9, 30, tzinfo=timezone.utc)  # default shift starts 09:00, 15 min grace

    record = attendance_service.check_in(db_session, tenant_a.company.id, engineer.id, now=late_check_in)

    assert record.is_late is True


def test_check_in_on_time_within_grace_period(db_session, tenant_a):
    _, engineer, _ = tenant_a.users["Employee"]
    on_time_check_in = datetime(2026, 6, 15, 9, 10, tzinfo=timezone.utc)

    record = attendance_service.check_in(db_session, tenant_a.company.id, engineer.id, now=on_time_check_in)

    assert record.is_late is False


def test_check_out_computes_overtime_past_shift_end(db_session, tenant_a):
    _, engineer, _ = tenant_a.users["Employee"]
    check_in_time = datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc)  # default shift ends 18:00
    check_out_time = datetime(2026, 6, 15, 19, 30, tzinfo=timezone.utc)

    attendance_service.check_in(db_session, tenant_a.company.id, engineer.id, now=check_in_time)
    record = attendance_service.check_out(db_session, tenant_a.company.id, engineer.id, now=check_out_time)

    assert record.overtime_hours == Decimal("1.50")


def test_check_out_no_overtime_within_shift_hours(db_session, tenant_a):
    _, engineer, _ = tenant_a.users["Employee"]
    check_in_time = datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc)
    check_out_time = datetime(2026, 6, 15, 17, 0, tzinfo=timezone.utc)

    attendance_service.check_in(db_session, tenant_a.company.id, engineer.id, now=check_in_time)
    record = attendance_service.check_out(db_session, tenant_a.company.id, engineer.id, now=check_out_time)

    assert record.overtime_hours == Decimal("0")


def test_attendance_isolated_per_company(client, tenant_a, tenant_b):
    headers_employee_a = tenant_a.auth_headers(client, "Employee")
    client.post("/api/v1/attendance/check-in", headers=headers_employee_a)

    headers_admin_b = tenant_b.auth_headers(client, "Admin")
    cross_tenant = client.get("/api/v1/attendance", headers=headers_admin_b)
    assert cross_tenant.status_code == 200
    assert cross_tenant.json()["total"] == 0
