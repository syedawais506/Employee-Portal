import logging
import sys
import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def configure_logging(debug: bool) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.DEBUG if debug else logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG if debug else logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        request_id_ctx.set(request_id)
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def get_logger(name: str):  # noqa: ANN201
    return structlog.get_logger(name)
