import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class NotificationResponse(ORMModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    entity_type: str | None
    entity_id: uuid.UUID | None
    is_read: bool
    created_at: datetime


class UnreadCountResponse(BaseModel):
    unread_count: int
