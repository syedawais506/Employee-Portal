import json
import uuid

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
        return set(json.loads(cached))

    permissions = role_repo.get_effective_permission_codes(db, user_id)
    redis_client.setex(_cache_key(user_id), CACHE_TTL_SECONDS, json.dumps(list(permissions)))
    return permissions


def invalidate(user_id: uuid.UUID) -> None:
    get_redis().delete(_cache_key(user_id))
