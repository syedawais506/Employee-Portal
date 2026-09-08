"""HR FAQ chatbot (Phase 13): per-company opt-in (`company.ai_chatbot_enabled`,
same convention as `require_hr_leave_approval`/`slack_webhook_url`), a
stateless `/ai/chat` endpoint grounded in the company's own leave types and
holiday calendar for everyone. Context scope then splits on whether the
caller holds `company.configure` (the same "Admin-only settings/insight"
signal used elsewhere, e.g. Integrations, the Headcount-by-Project chart):
Admin gets full company-wide leave data (every employee's balance, the
full pending-request queue), everyone else — Employee, Manager, HR,
Finance — only ever sees their own balance, reusing
`LeaveService.list_my_balances`/`list_company_balances` respectively. The
LLM call itself is mocked (`httpx.post`, same seam
`test_digests_and_webhooks.py` already uses for outbound webhook calls) so
these tests never hit the real Gemini API.
"""

from app.core.config import settings
from app.services import ai_chatbot_service as ai_chatbot_service_module


class _FakeGeminiResponse:
    def __init__(self, text: str):
        self._text = text

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"candidates": [{"content": {"parts": [{"text": self._text}]}}]}


class _CapturedGeminiCalls:
    def __init__(self, reply: str = "Mocked HR assistant reply."):
        self.reply = reply
        self.calls: list[dict] = []

    def __call__(self, url, params=None, json=None, timeout=None):
        self.calls.append({"url": url, "params": params, "json": json})
        return _FakeGeminiResponse(self.reply)


def _mock_gemini(monkeypatch, reply: str = "Mocked HR assistant reply.") -> _CapturedGeminiCalls:
    captured = _CapturedGeminiCalls(reply)
    monkeypatch.setattr(ai_chatbot_service_module.httpx, "post", captured)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    return captured


def _enable(client, headers_admin) -> None:
    response = client.patch("/api/v1/integrations/ai", headers=headers_admin, json={"enabled": True})
    assert response.status_code == 200, response.text
    assert response.json()["enabled"] is True


def _create_leave_type(client, headers_admin, name: str = "Annual Leave", quota: int = 12) -> str:
    response = client.post(
        "/api/v1/leave-types",
        headers=headers_admin,
        json={
            "name": name,
            "is_paid": True,
            "annual_quota_days": quota,
            "max_carry_forward_days": 0,
            "requires_attachment": False,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_leave_request(client, headers, leave_type_id: str, start: str, end: str) -> dict:
    response = client.post(
        "/api/v1/leave-requests",
        headers=headers,
        data={"leave_type_id": leave_type_id, "start_date": start, "end_date": end},
    )
    assert response.status_code == 201, response.text
    return response.json()


# -- admin toggle --------------------------------------------------------


def test_ai_integration_disabled_by_default(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    response = client.get("/api/v1/integrations/ai", headers=headers_admin)
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_admin_can_enable_and_disable(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin)

    disable = client.patch("/api/v1/integrations/ai", headers=headers_admin, json={"enabled": False})
    assert disable.status_code == 200
    assert disable.json()["enabled"] is False


def test_ai_integration_gated_on_company_configure(client, tenant_a):
    headers_hr = tenant_a.auth_headers(client, "HR")
    # HR holds employee.update but not company.configure.
    response = client.patch("/api/v1/integrations/ai", headers=headers_hr, json={"enabled": True})
    assert response.status_code == 403


# -- /auth/me reflects the flag ------------------------------------------


def test_auth_me_reflects_company_setting(client, tenant_a):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    before = client.get("/api/v1/auth/me", headers=headers_admin)
    assert before.json()["ai_chatbot_enabled"] is False

    _enable(client, headers_admin)

    after = client.get("/api/v1/auth/me", headers=headers_admin)
    assert after.json()["ai_chatbot_enabled"] is True


# -- /ai/chat -------------------------------------------------------------


def test_chat_rejected_when_not_enabled(client, tenant_a, monkeypatch):
    _mock_gemini(monkeypatch)
    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.post(
        "/api/v1/ai/chat", headers=headers_employee, json={"message": "How many sick days do I get?"}
    )
    assert response.status_code == 422


def test_chat_fails_clearly_when_server_has_no_api_key(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin)
    monkeypatch.setattr(settings, "gemini_api_key", None)

    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.post("/api/v1/ai/chat", headers=headers_employee, json={"message": "Hi"})
    assert response.status_code == 503


def test_chat_returns_reply_when_enabled_and_configured(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin)
    captured = _mock_gemini(monkeypatch, reply="You have 8 sick days remaining.")

    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.post(
        "/api/v1/ai/chat", headers=headers_employee, json={"message": "How many sick days do I have left?"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["reply"] == "You have 8 sick days remaining."
    assert len(captured.calls) == 1


def test_chat_context_includes_leave_types_and_own_balance_not_generic(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin)
    leave_type = client.post(
        "/api/v1/leave-types",
        headers=headers_admin,
        json={
            "name": "Sick Leave",
            "is_paid": True,
            "annual_quota_days": 10,
            "max_carry_forward_days": 0,
            "requires_attachment": False,
        },
    )
    assert leave_type.status_code == 201, leave_type.text
    captured = _mock_gemini(monkeypatch)

    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.post("/api/v1/ai/chat", headers=headers_employee, json={"message": "Tell me about sick leave"})
    assert response.status_code == 200, response.text

    system_prompt = captured.calls[0]["json"]["system_instruction"]["parts"][0]["text"]
    assert "Sick Leave" in system_prompt
    assert "Employee User's own leave balances" in system_prompt


def test_chat_history_is_replayed_to_the_model(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin)
    captured = _mock_gemini(monkeypatch)

    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.post(
        "/api/v1/ai/chat",
        headers=headers_employee,
        json={
            "message": "And what about unpaid leave?",
            "history": [
                {"role": "user", "content": "How many paid leave types are there?"},
                {"role": "assistant", "content": "There are two paid leave types."},
            ],
        },
    )
    assert response.status_code == 200, response.text

    contents = captured.calls[0]["json"]["contents"]
    assert contents[0] == {"role": "user", "parts": [{"text": "How many paid leave types are there?"}]}
    assert contents[1] == {"role": "model", "parts": [{"text": "There are two paid leave types."}]}
    assert contents[2] == {"role": "user", "parts": [{"text": "And what about unpaid leave?"}]}


def test_chat_disabled_for_one_company_even_if_enabled_for_another(client, tenant_a, tenant_b, monkeypatch):
    headers_admin_a = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin_a)
    _mock_gemini(monkeypatch)

    headers_employee_b = tenant_b.auth_headers(client, "Employee")
    response = client.post("/api/v1/ai/chat", headers=headers_employee_b, json={"message": "Hi"})
    assert response.status_code == 422


# -- admin vs. employee context scope ------------------------------------


def test_admin_chat_context_includes_other_employees_and_pending_queue(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin)
    leave_type_id = _create_leave_type(client, headers_admin)

    headers_hr = tenant_a.auth_headers(client, "HR")
    _create_leave_request(client, headers_hr, leave_type_id, "2026-11-10", "2026-11-11")

    captured = _mock_gemini(monkeypatch)
    response = client.post(
        "/api/v1/ai/chat", headers=headers_admin, json={"message": "Who has pending leave requests?"}
    )
    assert response.status_code == 200, response.text

    system_prompt = captured.calls[0]["json"]["system_instruction"]["parts"][0]["text"]
    assert "an ADMIN" in system_prompt
    assert "HR User" in system_prompt  # another employee's name — visible to Admin
    assert "Full pending leave request queue" in system_prompt
    assert "Company-wide leave balances" in system_prompt


def test_employee_chat_context_never_includes_other_employees_names(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin)
    leave_type_id = _create_leave_type(client, headers_admin)

    headers_hr = tenant_a.auth_headers(client, "HR")
    _create_leave_request(client, headers_hr, leave_type_id, "2026-11-10", "2026-11-11")

    captured = _mock_gemini(monkeypatch)
    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.post(
        "/api/v1/ai/chat", headers=headers_employee, json={"message": "Who else is on leave?"}
    )
    assert response.status_code == 200, response.text

    system_prompt = captured.calls[0]["json"]["system_instruction"]["parts"][0]["text"]
    assert "an EMPLOYEE" in system_prompt
    assert "HR User" not in system_prompt
    assert "Manager User" not in system_prompt
    assert "Full pending leave request queue" not in system_prompt
    assert "Company-wide leave balances" not in system_prompt


def test_manager_hr_and_finance_get_employee_scoped_context_not_admin(client, tenant_a, monkeypatch):
    headers_admin = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin)
    captured = _mock_gemini(monkeypatch)

    for role in ("Manager", "HR", "Finance"):
        headers = tenant_a.auth_headers(client, role)
        response = client.post("/api/v1/ai/chat", headers=headers, json={"message": "Hi"})
        assert response.status_code == 200, response.text
        system_prompt = captured.calls[-1]["json"]["system_instruction"]["parts"][0]["text"]
        assert "an EMPLOYEE" in system_prompt
        assert "an ADMIN" not in system_prompt


def test_upstream_failure_surfaces_as_503(client, tenant_a, monkeypatch):
    import httpx

    headers_admin = tenant_a.auth_headers(client, "Admin")
    _enable(client, headers_admin)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    def _boom(url, params=None, json=None, timeout=None):
        raise httpx.ConnectTimeout("simulated timeout")

    monkeypatch.setattr(ai_chatbot_service_module.httpx, "post", _boom)

    headers_employee = tenant_a.auth_headers(client, "Employee")
    response = client.post("/api/v1/ai/chat", headers=headers_employee, json={"message": "Hi"})
    assert response.status_code == 503
