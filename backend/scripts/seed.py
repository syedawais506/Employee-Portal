"""Seed demo data: platform Super Admin, two isolated demo companies each
with departments, default roles, and one employee per role.

Usage (from backend/):  python -m scripts.seed
"""

from datetime import date, datetime, timezone
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
from app.services.employee_service import employee_service
from app.services.onboarding_service import onboarding_service
from app.services.role_service import DEFAULT_ROLE_PERMISSIONS, role_service
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
        *, role_name: str, department_id, designation: str, first_name: str, last_name: str, manager_id=None
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
        first_name="Riley", last_name="Employee", manager_id=manager_employee.id,
    )
    make_user_and_employee(
        role_name="HR", department_id=hr_dept.id, designation="HR Generalist",
        first_name="Jordan", last_name="HR", manager_id=admin_employee.id,
    )
    make_user_and_employee(
        role_name="Finance", department_id=finance_dept.id, designation="Finance Analyst",
        first_name="Casey", last_name="Finance", manager_id=admin_employee.id,
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
