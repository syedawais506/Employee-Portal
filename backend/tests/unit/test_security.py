import pytest

from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("Sup3rSecret!")
    assert hashed != "Sup3rSecret!"
    assert verify_password("Sup3rSecret!", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token, jti, expires_in = create_access_token(user_id="user-1", company_id="company-1", role_ids=["role-1"])
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["company_id"] == "company-1"
    assert payload["type"] == TokenType.ACCESS.value
    assert payload["jti"] == jti
    assert expires_in > 0


def test_refresh_token_remember_me_extends_lifetime():
    _, _, ttl_default = create_refresh_token(user_id="user-1", remember_me=False)
    _, _, ttl_remember = create_refresh_token(user_id="user-1", remember_me=True)
    assert ttl_remember > ttl_default


def test_decode_rejects_tampered_token():
    token, _, _ = create_access_token(user_id="user-1", company_id=None, role_ids=[])
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ValueError):
        decode_token(tampered)
