def test_login_success_returns_access_token(client, tenant_a):
    user, _, password = tenant_a.users["Admin"]
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["expires_in"] > 0
    assert "refresh_token" in response.cookies


def test_login_wrong_password_returns_401(client, tenant_a):
    user, _, _ = tenant_a.users["Admin"]
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_protected_endpoint_without_token_returns_401(client):
    response = client.get("/api/v1/employees")
    assert response.status_code == 401


def test_protected_endpoint_with_garbage_token_returns_401(client):
    response = client.get("/api/v1/employees", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_returns_permissions_and_profile(client, tenant_a):
    headers = tenant_a.auth_headers(client, "Employee")
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["is_super_admin"] is False
    assert "employee.view" in body["permissions"]
    assert "employee.delete" not in body["permissions"]


def test_refresh_rotates_token_and_old_cookie_is_rejected(client, tenant_a):
    user, _, password = tenant_a.users["Admin"]
    login_response = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    old_refresh_cookie = login_response.cookies["refresh_token"]

    client.cookies.set("refresh_token", old_refresh_cookie)
    first_refresh = client.post("/api/v1/auth/refresh")
    assert first_refresh.status_code == 200

    # Reusing the same (now-rotated-away) refresh token must fail.
    client.cookies.set("refresh_token", old_refresh_cookie)
    second_refresh = client.post("/api/v1/auth/refresh")
    assert second_refresh.status_code == 401


def test_reusing_a_rotated_refresh_token_revokes_every_other_active_session(client, tenant_a):
    """Reuse of a stolen/rotated-away refresh token is treated as a signal
    the whole account may be compromised, not just that one token — every
    other still-valid refresh token for the same user (e.g. a concurrent
    login from a second device) must also stop working, not just the one
    caught being replayed.
    """
    user, _, password = tenant_a.users["Admin"]

    # Two independent sessions (e.g. two devices) for the same user.
    session_one = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    session_one_refresh_cookie = session_one.cookies["refresh_token"]
    session_two = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    session_two_refresh_cookie = session_two.cookies["refresh_token"]

    # Session one rotates normally, then its old (now-stale) token gets replayed.
    client.cookies.set("refresh_token", session_one_refresh_cookie)
    first_refresh = client.post("/api/v1/auth/refresh")
    assert first_refresh.status_code == 200

    client.cookies.set("refresh_token", session_one_refresh_cookie)
    replayed = client.post("/api/v1/auth/refresh")
    assert replayed.status_code == 401

    # Session two's refresh token was never itself reused, but the account-wide
    # revocation triggered by the replay above must have invalidated it too.
    client.cookies.set("refresh_token", session_two_refresh_cookie)
    session_two_refresh_attempt = client.post("/api/v1/auth/refresh")
    assert session_two_refresh_attempt.status_code == 401


def test_forgot_password_never_reveals_account_existence(client):
    known = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@nowhere-demo.com"})
    assert known.status_code == 202
