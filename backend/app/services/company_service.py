import secrets
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.rls import set_tenant_context
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import audit_service
from app.services.auth_service import auth_service
from app.services.role_service import DEFAULT_ROLE_PERMISSIONS, role_service

ADMIN_ROLE_NAME = "Admin"


class CompanyService:
    """Super-Admin-only operations. This is the one code path allowed to
    operate without a company_id filter — see docs/LLD.md section 4.
    """

    def __init__(self) -> None:
        self.company_repo = CompanyRepository()
        self.role_repo = RoleRepository()
        self.user_repo = UserRepository()

    def list_companies(self, db: Session, *, search: str | None, page: int, page_size: int):
        skip = (page - 1) * page_size
        return self.company_repo.list(db, search=search, skip=skip, limit=page_size)

    def get_company(self, db: Session, company_id: uuid.UUID) -> Company:
        company = self.company_repo.get(db, company_id)
        if company is None or company.deleted_at is not None:
            raise NotFoundError("Company not found")
        return company

    def create_company(
        self,
        db: Session,
        *,
        name: str,
        slug: str,
        admin_email: str,
        admin_first_name: str,
        admin_last_name: str,
        actor_user_id: uuid.UUID | None,
    ) -> Company:
        if self.company_repo.get_by_slug(db, slug) is not None:
            raise ConflictError("A company with this slug already exists")
        if self.user_repo.get_by_email(db, admin_email) is not None:
            raise ConflictError("A user with this email already exists")

        company = self.company_repo.create(db, name=name, slug=slug, status="active")
        # Bind the new tenant's id for the rest of this transaction so the
        # subsequent role/employee inserts satisfy the RLS WITH CHECK clause
        # under a strictly-enforced (non-superuser) Postgres role.
        set_tenant_context(db, str(company.id))

        for role_name in DEFAULT_ROLE_PERMISSIONS:
            role_service.create_default_role(db, company.id, role_name)

        admin_role = next(
            r for r in self.role_repo.list_roles(db, company.id) if r.name == ADMIN_ROLE_NAME
        )

        temp_password = secrets.token_urlsafe(16)
        admin_user = self.user_repo.create(
            db,
            company_id=company.id,
            email=admin_email,
            password_hash=hash_password(temp_password),
            is_active=True,
            is_verified=False,
        )
        self.user_repo.assign_roles(db, admin_user.id, [admin_role.id])

        from app.repositories.employee_repository import EmployeeRepository

        employee_repo = EmployeeRepository()
        employee_repo.create(
            db,
            company.id,
            user_id=admin_user.id,
            employee_code=employee_repo.next_employee_code(db, company.id, slug.upper()[:6]),
            first_name=admin_first_name,
            last_name=admin_last_name,
            employment_type="full_time",
            status="active",
        )

        auth_service.request_password_reset(db, admin_email)

        audit_service.record(
            db,
            company_id=company.id,
            actor_user_id=actor_user_id,
            entity_type="company",
            entity_id=company.id,
            action="create",
            after={"name": name, "slug": slug},
        )
        db.commit()
        return company

    def update_company(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        name: str | None,
        status: str | None,
        actor_user_id: uuid.UUID | None,
    ) -> Company:
        company = self.get_company(db, company_id)
        before = {"name": company.name, "status": company.status}
        if name is not None:
            company.name = name
        if status is not None:
            company.status = status
        db.flush()
        audit_service.record(
            db,
            company_id=company.id,
            actor_user_id=actor_user_id,
            entity_type="company",
            entity_id=company.id,
            action="update",
            before=before,
            after={"name": company.name, "status": company.status},
        )
        db.commit()
        return company

    def delete_company(self, db: Session, company_id: uuid.UUID, *, actor_user_id: uuid.UUID | None) -> None:
        from datetime import datetime, timezone

        company = self.get_company(db, company_id)
        company.deleted_at = datetime.now(timezone.utc)
        db.flush()
        audit_service.record(
            db,
            company_id=company.id,
            actor_user_id=actor_user_id,
            entity_type="company",
            entity_id=company.id,
            action="delete",
        )
        db.commit()


company_service = CompanyService()
