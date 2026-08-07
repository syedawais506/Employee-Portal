"""Seed demo data: platform Super Admin, two isolated demo companies each
with departments, default roles, and one employee per role.

Usage (from backend/):  python -m scripts.seed
"""

from datetime import date

from app.core.security import hash_password
from app.db.rls import set_tenant_context
from app.db.session import SessionLocal
from app.repositories.company_repository import CompanyRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.role_service import DEFAULT_ROLE_PERMISSIONS, role_service

DEMO_PASSWORD = "Demo@12345"
SUPER_ADMIN_PASSWORD = "SuperAdmin@12345"

company_repo = CompanyRepository()
department_repo = DepartmentRepository()
role_repo = RoleRepository()
user_repo = UserRepository()
employee_repo = EmployeeRepository()

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

    roles = {role_name: role_service.create_default_role(db, company.id, role_name) for role_name in DEFAULT_ROLE_PERMISSIONS}

    engineering = department_repo.create(db, company.id, name="Engineering", parent_department_id=None, cost_center_code="ENG")
    department_repo.create(db, company.id, name="Platform Team", parent_department_id=engineering.id, cost_center_code="ENG-PLT")
    hr_dept = department_repo.create(db, company.id, name="Human Resources", parent_department_id=None, cost_center_code="HR")
    finance_dept = department_repo.create(db, company.id, name="Finance", parent_department_id=None, cost_center_code="FIN")
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
    make_user_and_employee(
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


def main() -> None:
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


if __name__ == "__main__":
    main()
