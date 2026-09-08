import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user, get_db
from app.models.user import User
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.ai_chatbot_service import ai_chatbot_service
from app.services.auth_service import auth_service
from app.services.employee_service import employee_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee = employee_service.get_employee_by_user_id(db, current_user.id)
    # Same "Admin-only settings/insight" signal used elsewhere (Integrations,
    # the Headcount-by-Project dashboard chart) — Admin gets full company-wide
    # leave context, everyone else only ever sees their own data.
    is_admin = "company.configure" in auth_service.get_effective_permissions(db, current_user.id)
    reply = ai_chatbot_service.ask(
        db, company_id, employee, message=payload.message, history=payload.history, is_admin=is_admin
    )
    return ChatResponse(reply=reply)
