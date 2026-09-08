from __future__ import annotations

import uuid
from datetime import date

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ExternalServiceError, NotFoundError, ValidationAppError
from app.models.employee import Employee
from app.repositories.company_repository import CompanyRepository
from app.repositories.leave_repository import HolidayRepository, LeaveTypeRepository
from app.schemas.ai import ChatMessage
from app.services.audit_service import audit_service
from app.services.leave_service import leave_service

GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

SYSTEM_PROMPT = """You are the HR FAQ assistant for {company_name}, embedded in an employee portal.
Answer ONLY questions about this company's leave policy, holiday calendar, and the asking
employee's own leave balances, using the CONTEXT below. Be concise (2-4 sentences).
If asked something outside that scope, or something the context doesn't cover, say so plainly
and suggest the employee check the relevant page in the portal (Leave, Timesheets, etc.) or
contact HR directly — never guess or make up a policy or number that isn't in the context.
Never reveal or speculate about any other employee's personal data.

CONTEXT:
{context}
"""


class AIChatbotService:
    def __init__(self) -> None:
        self.company_repo = CompanyRepository()
        self.type_repo = LeaveTypeRepository()
        self.holiday_repo = HolidayRepository()

    def is_enabled(self, db: Session, company_id: uuid.UUID) -> bool:
        company = self.company_repo.get(db, company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company.ai_chatbot_enabled

    def set_enabled(
        self, db: Session, company_id: uuid.UUID, *, enabled: bool, actor_user_id: uuid.UUID
    ) -> bool:
        company = self.company_repo.get(db, company_id)
        if company is None:
            raise NotFoundError("Company not found")
        before = company.ai_chatbot_enabled
        company.ai_chatbot_enabled = enabled
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="ai_chatbot_settings",
            entity_id=company_id,
            action="update",
            before={"enabled": before},
            after={"enabled": enabled},
        )
        db.commit()
        return company.ai_chatbot_enabled

    def _build_context(self, db: Session, company_id: uuid.UUID, employee: Employee) -> str:
        lines: list[str] = []

        lines.append("Leave types:")
        for leave_type in self.type_repo.list_all(db, company_id):
            quota = (
                f"{leave_type.annual_quota_days} days/year"
                if leave_type.annual_quota_days is not None
                else "unlimited"
            )
            lines.append(
                f"- {leave_type.name}: {'paid' if leave_type.is_paid else 'unpaid'}, {quota}, "
                f"up to {leave_type.max_carry_forward_days} day(s) carry-forward, "
                f"{'requires' if leave_type.requires_attachment else 'no'} attachment required"
            )

        today = date.today()
        upcoming_holidays = [
            h
            for h in self.holiday_repo.list_all(db, company_id, year=today.year)
            if h.date >= today and (h.location is None or h.location == employee.location)
        ]
        lines.append("\nUpcoming holidays:")
        if upcoming_holidays:
            for holiday in upcoming_holidays[:10]:
                lines.append(f"- {holiday.date.isoformat()}: {holiday.name}")
        else:
            lines.append("- None scheduled for the rest of this year.")

        company = self.company_repo.get(db, company_id)
        hr_sign_off = company.require_hr_leave_approval if company else False
        lines.append(
            f"\nApproval process: every leave request needs Manager approval"
            f"{', followed by a required HR sign-off,' if hr_sign_off else ','} before it's final."
        )

        lines.append(f"\n{employee.full_name}'s own leave balances for {today.year}:")
        balances = leave_service.list_my_balances(db, company_id, employee.id, today.year)
        for balance in balances:
            if balance["available"] is None:
                lines.append(f"- {balance['leave_type_name']}: unlimited (used {balance['used']} so far)")
            else:
                lines.append(
                    f"- {balance['leave_type_name']}: {balance['available']} day(s) available "
                    f"(granted {balance['granted']}, carried forward {balance['carried_forward']}, "
                    f"used {balance['used']})"
                )

        return "\n".join(lines)

    def ask(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee: Employee,
        *,
        message: str,
        history: list[ChatMessage],
    ) -> str:
        if not self.is_enabled(db, company_id):
            raise ValidationAppError("The HR assistant is not enabled for your company")
        if not settings.gemini_api_key:
            raise ExternalServiceError("The HR assistant is not configured on this server")

        company = self.company_repo.get(db, company_id)
        company_name = company.name if company else "your company"
        context = self._build_context(db, company_id, employee)
        system_instruction = SYSTEM_PROMPT.format(company_name=company_name, context=context)

        contents = []
        for turn in history:
            role = "model" if turn.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": turn.content}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        try:
            response = httpx.post(
                GEMINI_URL,
                params={"key": settings.gemini_api_key},
                json={
                    "system_instruction": {"parts": [{"text": system_instruction}]},
                    "contents": contents,
                },
                timeout=45.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                "The HR assistant is temporarily unavailable — please try again shortly"
            ) from exc

        data = response.json()
        try:
            return str(data["candidates"][0]["content"]["parts"][0]["text"]).strip()
        except (KeyError, IndexError) as exc:
            raise ExternalServiceError("The HR assistant returned an unexpected response") from exc


ai_chatbot_service = AIChatbotService()
