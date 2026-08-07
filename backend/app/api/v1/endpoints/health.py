from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.redis_client import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    get_redis().ping()
    return {"status": "ok", "db": "ok", "redis": "ok"}
