import json
import uuid
from typing import cast

from sqlalchemy.orm import Session

from app.core.redis_client import get_redis
from app.repositories.role_repository import RoleRepository

CACHE_TTL_SECONDS = 300


def _cache_key(user_id: uuid.UUID) -> str:
    return f"permissions:{user_id}"


def get_effective_permissions(db: Session, user_id: uuid.UUID, role_repo: RoleRepository) -> set[str]:
    redis_client = get_redis()
    cached = redis_client.get(_cache_key(user_id))
    if cached is not None:
        # get_redis() always returns a sync client (decode_responses=True),
        # so this is always a str at runtime — the stub's return type is a
        # union only because redis-py's client class also supports async use.
        return set(json.loads(cast(str, cached)))

    permissions = role_repo.get_effective_permission_codes(db, user_id)
    redis_client.setex(_cache_key(user_id), CACHE_TTL_SECONDS, json.dumps(list(permissions)))
    return permissions


def invalidate(user_id: uuid.UUID) -> None:
    get_redis().delete(_cache_key(user_id))
