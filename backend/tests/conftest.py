import os
import uuid
from datetime import date

os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://portal:portal@localhost:5432/employee_portal_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

import fakeredis
import pytest
import redis as redis_module
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.core import redis_client as redis_client_module
from app.core.config import settings
from app.core.deps import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models import *  # noqa: F401,F403 — register all tables on Base.metadata
from app.repositories.company_repository import CompanyRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.user_repository import UserRepository
from app.services.role_service import DEFAULT_ROLE_PERMISSIONS, PERMISSION_CATALOG, role_service
from app.tasks.celery_app import celery_app

# Run Celery tasks synchronously, in-process, with no broker — email sending
# itself already no-ops safely when no SMTP server is reachable (see app/utils/email.py).
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True

engine = create_engine(settings.database_url, future=True)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _fake_redis():
    fake = fakeredis.FakeRedis(decode_responses=True)
    redis_client_module.get_redis.cache_clear()
    # Every caller does `from app.core.redis_client import get_redis` and then
    # calls redis.Redis.from_url(...) *lazily* inside that function, so
    # patching the underlying client class (rather than the already-bound
    # `get_redis` names in each importing module) is what actually takes effect.
    redis_module.Redis.from_url = classmethod(lambda cls, *a, **k: fake)  # type: ignore[method-assign]
    yield fake


@pytest.fixture(scope="session", autouse=True)
def _database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        for module, actions in PERMISSION_CATALOG.items():
            for action in actions:
                conn.execute(
                    text("INSERT INTO permission (id, module, action) VALUES (:id, :module, :action)"),
                    {"id": uuid.uuid4(), "module": module, "action": action},
                )
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(_database):
    """Isolates each test in a SAVEPOINT that's rolled back afterwards, even
    though service-layer code calls session.commit() internally. See the
    SQLAlchemy docs recipe "Joining a Session into an External Transaction".
    """
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TenantFixture:
    """Creates a fully seeded company (roles + one employee per role) for tests."""

    def __init__(self, db, name: str, slug: str):
        self.db = db
        self.company_repo = CompanyRepository()
        self.department_repo = DepartmentRepository()
        self.user_repo = UserRepository()
        self.employee_repo = EmployeeRepository()

        self.company = self.company_repo.create(db, name=name, slug=slug, status="active")
        self.roles = {
            role_name: role_service.create_default_role(db, self.company.id, role_name)
            for role_name in DEFAULT_ROLE_PERMISSIONS
        }
        self.department = self.department_repo.create(
            db, self.company.id, name="Engineering", parent_department_id=None, cost_center_code="ENG"
        )
        self.users: dict[str, tuple] = {}
        for role_name in DEFAULT_ROLE_PERMISSIONS:
            self.users[role_name] = self._make_user(role_name)
        db.commit()

    def _make_user(self, role_name: str):
        email = f"{role_name.lower()}@{self.company.slug}-demo.com"
        password = "Password@123"
        user = self.user_repo.create(
            self.db,
            company_id=self.company.id,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_verified=True,
        )
        self.user_repo.assign_roles(self.db, user.id, [self.roles[role_name].id])
        employee = self.employee_repo.create(
            self.db,
            self.company.id,
            user_id=user.id,
            employee_code=self.employee_repo.next_employee_code(
                self.db, self.company.id, self.company.slug.upper()[:6]
            ),
            first_name=role_name,
            last_name="User",
            department_id=self.department.id,
            employment_type="full_time",
            joining_date=date(2024, 1, 1),
            status="active",
        )
        return user, employee, password

    def login(self, client: TestClient, role_name: str) -> str:
        user, _, password = self.users[role_name]
        response = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    def auth_headers(self, client: TestClient, role_name: str) -> dict:
        return {"Authorization": f"Bearer {self.login(client, role_name)}"}


@pytest.fixture
def tenant_a(db_session):
    return TenantFixture(db_session, "Acme Corp", "acme")


@pytest.fixture
def tenant_b(db_session):
    return TenantFixture(db_session, "Globex Inc", "globex")
