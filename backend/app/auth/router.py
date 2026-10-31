import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    validate_password_strength,
    create_access_token,
)
from app.models import User
from app.schemas import (
    UserRegister,
    UserLogin,
    StaffCreate,
    UserResponse,
    TokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    PaginatedResponse,
)
from app.common.dependencies import get_current_user, require_admin, require_staff_or_admin, record_audit_log
from app.common.email import send_email

router = APIRouter(prefix="/auth", tags=["Authentication & Users"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_customer(payload: UserRegister, db: Session = Depends(get_db)):
    validate_password_strength(payload.password)

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        role="customer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled.",
        )

    token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/staff", response_model=UserResponse, dependencies=[Depends(require_admin)])
def create_staff(
    payload: StaffCreate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    validate_password_strength(payload.password)

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    staff_user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        role="staff",
        is_active=True,
    )
    db.add(staff_user)
    record_audit_log(
        db,
        entity_type="user",
        entity_id=staff_user.id,
        action="created_staff",
        new_value={"name": staff_user.name, "email": staff_user.email},
        user_id=current_admin.id,
    )
    db.commit()
    db.refresh(staff_user)
    return UserResponse.model_validate(staff_user)


@router.post("/reset-password/request")
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        return {"message": "If this email is registered, a password reset link has been dispatched."}

    token = str(uuid.uuid4())
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    reset_link = f"http://localhost:3000/reset-password?token={token}"
    html_msg = f"""
    <h2>Password Reset Request</h2>
    <p>Hi {user.name},</p>
    <p>You requested a password reset for your Brightloop Software account.</p>
    <p><a href="{reset_link}" style="background:#2563eb;color:#ffffff;padding:8px 16px;text-decoration:none;border-radius:4px;">Reset Password</a></p>
    <p>Or use token: <code>{token}</code></p>
    <p>This link expires in 1 hour.</p>
    """
    send_email(
        to_email=user.email,
        subject="Reset Your Brightloop Software Password",
        html_content=html_msg,
    )

    return {
        "message": "If this email is registered, a password reset link has been dispatched.",
        "reset_token": token,
    }


@router.post("/reset-password/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    validate_password_strength(payload.new_password)

    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )

    user.password_hash = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Password has been successfully updated. You may now log in."}


@router.get("/users", response_model=PaginatedResponse, dependencies=[Depends(require_staff_or_admin)])
def list_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if search:
        search_fmt = f"%{search.lower()}%"
        query = query.filter(or_(func.lower(User.name).like(search_fmt), func.lower(User.email).like(search_fmt)))

    total = query.count()
    items = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )
