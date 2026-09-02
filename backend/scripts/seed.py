"""Seed demo data: platform Super Admin, two isolated demo companies each
with departments, default roles, and one employee per role.

Usage (from backend/):  python -m scripts.seed
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.core.security import hash_password
from app.db.rls import set_tenant_context
from app.db.session import SessionLocal
from app.repositories.company_repository import CompanyRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.onboarding_repository import DocumentTypeRepository, OnboardingInviteRepository
from app.repositories.project_repository import ClientRepository, ProjectMemberRepository, ProjectRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.asset_service import asset_service
from app.services.attendance_service import attendance_service
from app.services.employee_service import employee_service
from app.services.leave_service import leave_service
from app.services.onboarding_service import onboarding_service
from app.services.report_service import report_service
from app.services.role_service import DEFAULT_ROLE_PERMISSIONS, role_service
from app.services.timesheet_service import timesheet_service
from app.utils.storage import ensure_bucket_exists, upload_document

DEMO_PASSWORD = "Demo@12345"
SUPER_ADMIN_PASSWORD = "SuperAdmin@12345"

company_repo = CompanyRepository()
department_repo = DepartmentRepository()
role_repo = RoleRepository()
user_repo = UserRepository()
employee_repo = EmployeeRepository()
document_type_repo = DocumentTypeRepository()
invite_repo = OnboardingInviteRepository()
client_repo = ClientRepository()
project_repo = ProjectRepository()
project_member_repo = ProjectMemberRepository()

credentials: list[tuple[str, str, str]] = []


def seed_super_admin(db) -> None:
    email = "superadmin@employee-portal-demo.com"
    if user_repo.get_by_email(db, email) is not None:
        return
    user_repo.create(
        db,
        company_id=None,
        email=email,
        password_hash=hash_password(SUPER_ADMIN_PASSWORD),
        is_super_admin=True,
        is_active=True,
        is_verified=True,
    )
    credentials.append(("Super Admin", email, SUPER_ADMIN_PASSWORD))


def seed_company(db, *, name: str, slug: str) -> None:
    if company_repo.get_by_slug(db, slug) is not None:
        return

    company = company_repo.create(db, name=name, slug=slug, status="active")
    set_tenant_context(db, str(company.id))

    roles = {
        role_name: role_service.create_default_role(db, company.id, role_name)
        for role_name in DEFAULT_ROLE_PERMISSIONS
    }

    engineering = department_repo.create(
        db, company.id, name="Engineering", parent_department_id=None, cost_center_code="ENG"
    )
    department_repo.create(
        db, company.id, name="Platform Team", parent_department_id=engineering.id, cost_center_code="ENG-PLT"
    )
    hr_dept = department_repo.create(
        db, company.id, name="Human Resources", parent_department_id=None, cost_center_code="HR"
    )
    finance_dept = department_repo.create(
        db, company.id, name="Finance", parent_department_id=None, cost_center_code="FIN"
    )
    department_repo.create(db, company.id, name="Sales", parent_department_id=None, cost_center_code="SALES")

    def make_user_and_employee(
        *,
        role_name: str,
        department_id,
        designation: str,
        first_name: str,
        last_name: str,
        manager_id=None,
        location: str = "United States",
    ):
        email = f"{role_name.lower()}@{slug}-demo.com"
        user = user_repo.create(
            db,
            company_id=company.id,
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            is_active=True,
            is_verified=True,
        )
        user_repo.assign_roles(db, user.id, [roles[role_name].id])
        employee = employee_repo.create(
            db,
            company.id,
            user_id=user.id,
            employee_code=employee_repo.next_employee_code(db, company.id, slug.upper()[:6]),
            first_name=first_name,
            last_name=last_name,
            department_id=department_id,
            designation=designation,
            manager_id=manager_id,
            employment_type="full_time",
            location=location,
            joining_date=date(2024, 1, 15),
            status="active",
        )
        credentials.append((f"{name} — {role_name}", email, DEMO_PASSWORD))
        return employee

    admin_employee = make_user_and_employee(
        role_name="Admin", department_id=engineering.id, designation="Administrator",
        first_name="Alex", last_name="Admin",
    )
    manager_employee = make_user_and_employee(
        role_name="Manager", department_id=engineering.id, designation="Engineering Manager",
        first_name="Morgan", last_name="Manager", manager_id=admin_employee.id,
    )
    engineer_employee = make_user_and_employee(
        role_name="Employee", department_id=engineering.id, designation="Software Engineer",
        first_name="Riley", last_name="Employee", manager_id=manager_employee.id, location="India",
    )
    make_user_and_employee(
        role_name="HR", department_id=hr_dept.id, designation="HR Generalist",
        first_name="Jordan", last_name="HR", manager_id=admin_employee.id,
    )
    finance_employee = make_user_and_employee(
        role_name="Finance", department_id=finance_dept.id, designation="Finance Analyst",
        first_name="Casey", last_name="Finance", manager_id=admin_employee.id, location="India",
    )

    # Onboarding demo: a document checklist plus one new hire already
    # sitting in the HR review queue, so the Onboarding screens aren't empty
    # on first login.
    document_types = [
        document_type_repo.create(db, company.id, name="Resume", is_required=True, sort_order=1),
        document_type_repo.create(db, company.id, name="Government ID", is_required=True, sort_order=2),
        document_type_repo.create(db, company.id, name="PAN Card", is_required=False, sort_order=3),
    ]
    new_hire = employee_service.create_employee(
        db,
        company.id,
        email=f"newhire@{slug}-demo.com",
        first_name="Taylor",
        last_name="NewHire",
        phone=None,
        department_id=engineering.id,
        designation="Associate Engineer",
        manager_id=manager_employee.id,
        employment_type="full_time",
        location="United States",
        joining_date=date(2026, 3, 1),
        role_ids=[roles["Employee"].id],
        actor_user_id=admin_employee.user_id,
    )
    _advance_demo_onboarding_to_submitted(db, company_id=company.id, employee=new_hire, document_types=document_types)

    # Projects demo: one billable client project and one internal
    # non-billable project, so the Projects screen isn't empty on first login.
    client = client_repo.create(
        db,
        company.id,
        name="Northwind Trading Co",
        contact_name="Jamie Lee",
        contact_email="jamie.lee@northwind-demo.com",
        contact_phone="+1-555-0100",
    )
    client_project = project_repo.create(
        db,
        company.id,
        client_id=client.id,
        name="Website Revamp",
        budget=Decimal("50000.00"),
        is_billable=True,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        status="active",
    )
    project_member_repo.add(db, client_project.id, manager_employee.id, "manager")
    project_member_repo.add(db, client_project.id, engineer_employee.id, "member")

    internal_project = project_repo.create(
        db,
        company.id,
        client_id=None,
        name="Internal Tooling",
        budget=None,
        is_billable=False,
        start_date=date(2026, 2, 1),
        end_date=None,
        status="active",
    )
    project_member_repo.add(db, internal_project.id, admin_employee.id, "manager")
    project_member_repo.add(db, internal_project.id, engineer_employee.id, "member")
    project_member_repo.add(db, internal_project.id, finance_employee.id, "member")

    # Timesheets demo: a submitted (pending), an approved, and a rejected
    # period so the My Timesheet / Approvals / Dashboard screens all have
    # real data on first login rather than empty states.
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    for day_offset, hours in ((0, Decimal("4.00")), (1, Decimal("4.50"))):
        timesheet_service.create_entry(
            db, company.id, engineer_employee.id,
            project_id=client_project.id, entry_date=monday + timedelta(days=day_offset),
            hours=hours, is_billable=True, work_type="office",
            description="Feature implementation", actor_user_id=engineer_employee.user_id,
        )
    timesheet_service.submit_period(
        db, company.id, engineer_employee.id, monday, monday + timedelta(days=1),
        actor_user_id=engineer_employee.user_id,
    )

    for day_offset, hours in ((0, Decimal("3.00")), (1, Decimal("5.00"))):
        timesheet_service.create_entry(
            db, company.id, manager_employee.id,
            project_id=client_project.id, entry_date=monday + timedelta(days=day_offset),
            hours=hours, is_billable=True, work_type="remote",
            description="Client coordination", actor_user_id=manager_employee.user_id,
        )
    manager_submission = timesheet_service.submit_period(
        db, company.id, manager_employee.id, monday, monday + timedelta(days=1),
        actor_user_id=manager_employee.user_id,
    )
    timesheet_service.approve_submission(db, company.id, manager_submission.id, actor_user_id=admin_employee.user_id)

    timesheet_service.create_entry(
        db, company.id, finance_employee.id,
        project_id=internal_project.id, entry_date=monday,
        hours=Decimal("6.00"), is_billable=False, work_type="office",
        description="Cost tracking setup", actor_user_id=finance_employee.user_id,
    )
    finance_submission = timesheet_service.submit_period(
        db, company.id, finance_employee.id, monday, monday, actor_user_id=finance_employee.user_id
    )
    timesheet_service.reject_submission(
        db, company.id, finance_submission.id,
        reason="Please split hours by task and add more detail to the description.",
        actor_user_id=manager_employee.user_id,
    )

    # Leave demo: an annual/sick/unpaid leave type catalog, one holiday, and
    # a pending, an approved, and a rejected request so the My Leave /
    # Approvals / Balances / Dashboard screens all have real data.
    annual_leave = leave_service.create_leave_type(
        db, company.id,
        name="Annual Leave", is_paid=True, annual_quota_days=20, max_carry_forward_days=5,
        requires_attachment=False, actor_user_id=admin_employee.user_id,
    )
    sick_leave = leave_service.create_leave_type(
        db, company.id,
        name="Sick Leave", is_paid=True, annual_quota_days=10, max_carry_forward_days=0,
        requires_attachment=True, actor_user_id=admin_employee.user_id,
    )
    leave_service.create_leave_type(
        db, company.id,
        name="Unpaid Leave", is_paid=False, annual_quota_days=None, max_carry_forward_days=0,
        requires_attachment=False, actor_user_id=admin_employee.user_id,
    )
    leave_service.create_holiday(
        db, company.id,
        date=date(today.year, 12, 25), name="Christmas Day", location=None, actor_user_id=admin_employee.user_id,
    )
    leave_service.create_holiday(
        db, company.id,
        date=date(today.year, 11, 1), name="Diwali", location="India", actor_user_id=admin_employee.user_id,
    )

    leave_week1 = monday + timedelta(weeks=2)
    leave_service.create_request(
        db, company.id,
        caller_employee_id=engineer_employee.id, requested_employee_id=None, can_act_for_others=False,
        leave_type_id=annual_leave.id, start_date=leave_week1, end_date=leave_week1 + timedelta(days=1),
        reason="Family trip", attachment=None, actor_user_id=engineer_employee.user_id,
    )

    leave_week2 = monday + timedelta(weeks=3)
    approved_request = leave_service.create_request(
        db, company.id,
        caller_employee_id=manager_employee.id, requested_employee_id=None, can_act_for_others=False,
        leave_type_id=sick_leave.id, start_date=leave_week2, end_date=leave_week2,
        reason="Medical appointment",
        attachment=(b"Demo medical certificate content.", "medical_certificate.pdf", "application/pdf"),
        actor_user_id=manager_employee.user_id,
    )
    leave_service.approve_request(db, company.id, approved_request.id, actor_user_id=admin_employee.user_id)

    leave_week3 = monday + timedelta(weeks=4)
    rejected_request = leave_service.create_request(
        db, company.id,
        caller_employee_id=finance_employee.id, requested_employee_id=None, can_act_for_others=False,
        leave_type_id=annual_leave.id, start_date=leave_week3, end_date=leave_week3,
        reason="Personal errand", attachment=None, actor_user_id=finance_employee.user_id,
    )
    leave_service.reject_request(
        db, company.id, rejected_request.id,
        reason="This overlaps with a planned client deliverable — please pick different dates.",
        actor_user_id=manager_employee.user_id,
    )

    # Assets demo: a laptop/monitor catalog, one asset currently assigned
    # (with history), and one still sitting available, so the Assets screen
    # has real data on first login.
    laptop_type = asset_service.create_asset_type(db, company.id, name="Laptop", actor_user_id=admin_employee.user_id)
    asset_service.create_asset_type(db, company.id, name="Monitor", actor_user_id=admin_employee.user_id)

    assigned_laptop = asset_service.create_asset(
        db, company.id,
        asset_type_id=laptop_type.id, asset_tag=f"{slug.upper()}-LT-001", name="Dell Latitude 5440",
        purchase_date=date(2025, 6, 1), warranty_expiry=date(2028, 6, 1),
        notes=None, actor_user_id=admin_employee.user_id,
    )
    asset_service.assign_asset(
        db, company.id, assigned_laptop.id, employee_id=engineer_employee.id, actor_user_id=admin_employee.user_id
    )

    asset_service.create_asset(
        db, company.id,
        asset_type_id=laptop_type.id, asset_tag=f"{slug.upper()}-LT-002", name="Dell Latitude 5440",
        purchase_date=date(2025, 6, 1), warranty_expiry=date(2028, 6, 1),
        notes="Spare — available for the next new hire", actor_user_id=admin_employee.user_id,
    )

    # Attendance demo: two days of history (one on-time, one late-with-overtime)
    # plus a check-in-only record for today, so My Attendance / Company
    # Attendance / Today all have real data on first login. Backdated records
    # can't go through attendance_service.check_in/check_out (those always
    # operate on "today"), so this pokes the repository directly with explicit
    # dates — same reasoning as _advance_demo_onboarding_to_submitted below.
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)
    for day in (day_before, yesterday):
        attendance_service.record_repo.create(
            db, company.id,
            employee_id=engineer_employee.id, attendance_date=day,
            check_in_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=9, minute=5),
            check_out_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=18, minute=0),
            is_late=False, overtime_hours=Decimal("0"),
        )
        attendance_service.record_repo.create(
            db, company.id,
            employee_id=manager_employee.id, attendance_date=day,
            check_in_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=9, minute=45),
            check_out_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=19, minute=30),
            is_late=True, overtime_hours=Decimal("1.50"),
        )
    attendance_service.record_repo.create(
        db, company.id,
        employee_id=admin_employee.id, attendance_date=today,
        check_in_at=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).replace(hour=8, minute=55),
        check_out_at=None, is_late=False, overtime_hours=Decimal("0"),
    )

    # Reporting demo: a couple of saved reports so the Reports screen isn't
    # empty on first login.
    report_service.create_saved_report(
        db, company.id,
        name="Active Employees", module="employee", filters={"status": "active"},
        actor_user_id=admin_employee.user_id,
    )
    report_service.create_saved_report(
        db, company.id,
        name="Pending Leave Requests", module="leave", filters={"status": "pending"},
        actor_user_id=admin_employee.user_id,
    )


def _advance_demo_onboarding_to_submitted(db, *, company_id, employee, document_types) -> None:
    """Simulates the new hire having set a password and uploaded every
    required document, so HR/Admin demo accounts see a populated review
    queue immediately. Pokes state directly rather than going through the
    public token endpoints, since there's no real onboarding link to follow
    in a non-interactive seed script.
    """
    invite = invite_repo.get_by_employee_id(db, employee.id)
    if invite is None:
        return

    employee.user.password_hash = hash_password(DEMO_PASSWORD)
    invite.used_at = datetime.now(timezone.utc)

    for doc_type in document_types:
        if not doc_type.is_required:
            continue
        key = f"seed/{company_id}/{employee.id}/{doc_type.id}.pdf"
        upload_document(key=key, content=b"Demo document content for seeding.", content_type="application/pdf")
        onboarding_service.employee_document_repo.upsert(
            db,
            company_id=company_id,
            employee_id=employee.id,
            document_type_id=doc_type.id,
            file_key=key,
            original_filename=f"{doc_type.name}.pdf",
            content_type="application/pdf",
            size_bytes=35,
        )

    employee.onboarding_status = "submitted"
    db.flush()


def main() -> None:
    ensure_bucket_exists()
    db = SessionLocal()
    try:
        seed_super_admin(db)
        seed_company(db, name="Acme Corp", slug="acme")
        seed_company(db, name="Globex Inc", slug="globex")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("\nSeed complete. Demo credentials:\n")
    print(f"{'Role':30} {'Email':30} {'Password'}")
    print("-" * 80)
    for role_label, email, password in credentials:
        print(f"{role_label:30} {email:30} {password}")
    print(
        "\nEach company also has a 'Taylor NewHire' employee sitting in the "
        "onboarding review queue (documents submitted, awaiting HR review) — "
        "log in as an HR or Admin demo user and open Onboarding to see it."
    )


if __name__ == "__main__":
    main()
