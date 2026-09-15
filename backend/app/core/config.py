from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Employee Portal"
    app_env: str = "development"
    debug: bool = False
    secret_key: str
    api_v1_prefix: str = "/api/v1"

    cors_origins: str = "http://localhost:5173"

    database_url: str
    # Set only for the migration-running container/command — points at the
    # superuser role (POSTGRES_USER) that owns the schema and can run DDL.
    # database_url (above) is what the app connects as at runtime: a
    # restricted, non-superuser role, so RLS policies actually apply (see
    # docker/postgres-initdb/01-create-app-role.sh). Falls back to
    # database_url when unset, e.g. for local non-Docker dev with one role.
    migration_database_url: str | None = None
    # Postgres' own default max_connections is 100. Every process that
    # imports app.db.session gets its own independent pool of this size
    # (gunicorn's 4 workers, celery-worker, celery-beat each hold one) — see
    # docker-compose.yml's celery worker --concurrency for the other half of
    # this budget. Sized so worst case (all pools fully checked out at once)
    # stays comfortably under 100, leaving headroom for direct/admin
    # connections (psql, migrations).
    db_pool_size: int = 5
    db_max_overflow: int = 5

    redis_url: str = "redis://localhost:6379/0"

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_token_remember_me_expire_days: int = 30

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "no-reply@employee-portal.local"
    smtp_from_name: str = ""
    smtp_use_tls: bool = False

    s3_endpoint_url: str = "http://localhost:9000"
    # Browser-reachable base URL for presigned download links. In Docker
    # Compose, s3_endpoint_url is the internal "http://minio:9000" hostname —
    # fine for the backend to reach MinIO, useless for a browser presigned
    # URL, which is signed against (and must be fetched from) this host
    # instead. Left blank, it falls back to s3_endpoint_url, which is
    # correct for local (non-Docker) dev where both are already the same
    # localhost address.
    s3_public_endpoint_url: str = ""
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "employee-portal"
    s3_region: str = "us-east-1"

    frontend_base_url: str = "http://localhost:5173"

    auth_rate_limit: str = "5/minute"

    # Platform-wide key shared by every company that opts into the HR FAQ
    # chatbot (company.ai_chatbot_enabled) — no per-tenant "bring your own
    # key" yet, see docs/ROADMAP.md Phase 13.
    gemini_api_key: str | None = None
    # Per-user, per-minute cap on /ai/chat — it's an authenticated endpoint
    # that calls a paid external API, so IP-based limiting isn't the right
    # tool (shared office IPs, etc.); enforced directly against Redis in
    # ai_chatbot_service, keyed by user id.
    ai_chat_rate_limit_per_minute: int = 10

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def s3_public_endpoint_url_effective(self) -> str:
        return self.s3_public_endpoint_url or self.s3_endpoint_url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
