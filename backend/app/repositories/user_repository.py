import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import UserRole
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
