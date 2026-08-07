from functools import lru_cache

from pydantic import Field
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
    smtp_use_tls: bool = False

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "employee-portal"
    s3_region: str = "us-east-1"

    frontend_base_url: str = "http://localhost:5173"

    auth_rate_limit: str = "5/minute"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
