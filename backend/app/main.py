import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging, get_logger
from app.core.rate_limit import limiter
from app.services.notification_ws import connection_manager
from app.utils.storage import ensure_bucket_exists

configure_logging(settings.debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    connection_manager.loop = asyncio.get_running_loop()
    connection_manager.start_redis_listener()
    try:
        ensure_bucket_exists()
    except Exception:
        logger.warning("s3_bucket_bootstrap_failed", bucket=settings.s3_bucket_name)
    yield
    connection_manager.stop_redis_listener()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    # Swagger UI and the raw OpenAPI schema hand an attacker a full map of
    # every endpoint, request shape, and auth scheme — fine in dev, not
    # something to expose publicly in production.
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
    openapi_url="/openapi.json" if settings.app_env != "production" else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(  # noqa: ARG005
        status_code=429,
        content={"error": {"code": "RATE_LIMITED", "message": "Too many requests", "details": None}},
    ),
)
app.add_middleware(SlowAPIMiddleware)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path not in ("/docs", "/redoc"):
            # This backend is a JSON API with no legitimate reason to load
            # scripts/styles/frames of its own. /docs and /redoc (dev-only —
            # disabled entirely in production above) are the only routes that
            # render real HTML and need their CDN-hosted Swagger/ReDoc assets.
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if settings.app_env != "development":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(health.router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
