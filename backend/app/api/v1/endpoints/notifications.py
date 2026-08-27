import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.core.security import TokenType, decode_token
from app.db.session import SessionLocal
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.notification import NotificationResponse, UnreadCountResponse
from app.services.notification_service import notification_service
from app.services.notification_ws import connection_manager

router = APIRouter(prefix="/notifications", tags=["notifications"])

_user_repo = UserRepository()


@router.get("", response_model=Page[NotificationResponse])
def list_my_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.list_my_notifications(
        db, company_id, current_user.id, unread_only=unread_only, page=page, page_size=page_size
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UnreadCountResponse(unread_count=notification_service.get_unread_count(db, company_id, current_user.id))


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = notification_service.mark_read(db, company_id, current_user.id, notification_id)
    if notification is None:
        raise NotFoundError("Notification not found")
    return notification


@router.post("/read-all")
def mark_all_notifications_read(
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = notification_service.mark_all_read(db, company_id, current_user.id)
    return {"marked_read": count}


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket, token: str = Query(...)):
    # A short-lived session just for the handshake's auth lookup — unlike
    # the REST endpoints above, this connection then stays open for the
    # life of the WebSocket, so holding a pooled DB session the whole time
    # (via the usual Depends(get_db)) would tie up a connection per open tab.
    db = SessionLocal()
    try:
        payload = decode_token(token)
        if payload.get("type") != TokenType.ACCESS.value:
            raise ValueError("Invalid token type")
        user = _user_repo.get_by_id(db, uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise ValueError("User not found or inactive")
    except (ValueError, KeyError):
        await websocket.close(code=4401)
        return
    finally:
        db.close()

    await connection_manager.connect(user.id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(user.id, websocket)
