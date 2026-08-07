from __future__ import annotations

import io
from datetime import date

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.models.employee import Employee

_STYLES = getSampleStyleSheet()


def render_offer_letter_pdf(employee: Employee) -> bytes:
    """Renders a simple offer letter as a PDF. Not per-company customizable
    yet — see docs/ROADMAP.md Phase 2 scope. Real Employee/Company data,
    not a stub: pulls designation, department, and joining date live.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, topMargin=1 * inch, bottomMargin=1 * inch)

    joining_date = employee.joining_date.strftime("%B %d, %Y") if employee.joining_date else "to be confirmed"
    today = date.today().strftime("%B %d, %Y")

    story = [
        Paragraph(employee.company.name, _STYLES["Title"]),
        Spacer(1, 0.3 * inch),
        Paragraph(today, _STYLES["Normal"]),
        Spacer(1, 0.2 * inch),
        Paragraph(f"Dear {employee.full_name},", _STYLES["Normal"]),
        Spacer(1, 0.2 * inch),
        Paragraph(
            f"We are pleased to confirm your offer of employment with {employee.company.name} as "
            f"<b>{employee.designation or 'a member of our team'}</b>"
            + (f" in the {employee.department.name} department" if employee.department else "")
            + f", starting on <b>{joining_date}</b>. Your employment type is "
            f"<b>{employee.employment_type.replace('_', ' ')}</b>.",
            _STYLES["Normal"],
        ),
        Spacer(1, 0.2 * inch),
        Paragraph(
            "This letter confirms the key terms of your offer. Detailed terms and conditions of "
            "employment will be provided separately.",
            _STYLES["Normal"],
        ),
        Spacer(1, 0.4 * inch),
        Paragraph("Welcome to the team!", _STYLES["Normal"]),
        Spacer(1, 0.4 * inch),
        Paragraph(f"Employee ID: {employee.employee_code}", _STYLES["Normal"]),
    ]

    doc.build(story)
    return buffer.getvalue()
