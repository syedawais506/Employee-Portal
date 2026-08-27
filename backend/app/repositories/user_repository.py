import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Permission, RolePermission, UserRole
from app.models.user import User


class UserRepository:
    """Not tenant-scoped: auth lookups happen by email/id before company
    context is known (e.g. during login). Tenant checks happen one layer up
    once the user's company_id is read from the row itself.
    """

    def get_by_id(self, db: Session, id: uuid.UUID) -> User | None:
        return db.get(User, id)

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()

    def create(self, db: Session, **fields) -> User:
        fields["email"] = fields["email"].lower()
        user = User(**fields)
        db.add(user)
        db.flush()
        return user

    def assign_roles(self, db: Session, user_id: uuid.UUID, role_ids: list[uuid.UUID]) -> None:
        for role_id in role_ids:
            db.add(UserRole(user_id=user_id, role_id=role_id))
        db.flush()

    def get_role_ids(self, db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(UserRole.role_id).where(UserRole.user_id == user_id)
        return [row[0] for row in db.execute(stmt).all()]

    def list_by_permission(self, db: Session, company_id: uuid.UUID, module: str, action: str) -> list[User]:
        """Every active user in a company who holds module.action via any
        assigned role — used to fan out a notification to, e.g., "everyone
        who can review onboarding" rather than a single recipient.
        """
        stmt = (
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(RolePermission, RolePermission.role_id == UserRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                Permission.module == module,
                Permission.action == action,
                User.company_id == company_id,
                User.is_active.is_(True),
            )
            .distinct()
        )
        return list(db.execute(stmt).scalars().all())
