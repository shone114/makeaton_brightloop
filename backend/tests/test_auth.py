import pytest
from app.core.security import validate_password_strength, verify_password, get_password_hash, create_access_token, decode_access_token
from fastapi import HTTPException
from app.auth.router import register_customer, login
from app.schemas import UserRegister, UserLogin


def test_password_strength_valid():
    validate_password_strength("Brightloop@2026!")


def test_password_strength_too_short():
    with pytest.raises(HTTPException) as exc:
        validate_password_strength("Ab1!234")
    assert "more than 8 characters" in exc.value.detail


def test_password_strength_no_uppercase():
    with pytest.raises(HTTPException) as exc:
        validate_password_strength("brightloop@2026!")
    assert "uppercase" in exc.value.detail


def test_password_strength_no_lowercase():
    with pytest.raises(HTTPException) as exc:
        validate_password_strength("BRIGHTLOOP@2026!")
    assert "lowercase" in exc.value.detail


def test_password_strength_no_special():
    with pytest.raises(HTTPException) as exc:
        validate_password_strength("Brightloop2026")
    assert "special character" in exc.value.detail


def test_password_hashing():
    pwd = "SecurePassword@123!"
    hashed = get_password_hash(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword@123!", hashed) is False


def test_jwt_token_creation_and_decode():
    token = create_access_token({"sub": "user_123", "role": "admin"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user_123"
    assert payload["role"] == "admin"


def test_auth_registration_and_login_flow(db_session):
    import uuid
    u_email = f"test_user_{uuid.uuid4().hex[:6]}@brightloop.com"
    payload = UserRegister(
        name="Unit Test User",
        email=u_email,
        password="TestUser@1234!",
    )
    reg_res = register_customer(payload, db_session)
    assert reg_res.access_token is not None
    assert reg_res.user.email == u_email
    assert reg_res.user.role == "customer"

    # Login
    login_payload = UserLogin(
        email=u_email,
        password="TestUser@1234!",
    )
    login_res = login(login_payload, db_session)
    assert login_res.access_token is not None
    assert login_res.user.name == "Unit Test User"
