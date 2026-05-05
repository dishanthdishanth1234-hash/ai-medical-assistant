"""Registration (email OTP), login, and profile endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from deps import get_current_user
from models.orm import PasswordResetOtp, RegistrationOtp, User
from models.schemas import (
    MessageResponse,
    PasswordResetRequest,
    PasswordResetVerifyRequest,
    ProfileUpdate,
    SendOtpRequest,
    SendOtpResponse,
    Token,
    UserLogin,
    UserOut,
    UserRegister,
)
from security import create_access_token, hash_password, verify_password
from services.email_otp import send_otp_email
from services.otp_utils import generate_otp_digits, hash_otp, otp_expires_at

router = APIRouter(prefix="", tags=["auth"])


@router.post("/register/send-otp", response_model=SendOtpResponse)
def register_send_otp(payload: SendOtpRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="Email already registered")
    code = generate_otp_digits()
    h = hash_otp(email, code)
    exp = otp_expires_at()
    row = db.get(RegistrationOtp, email)
    if row:
        row.code_hash = h
        row.expires_at = exp
    else:
        db.add(RegistrationOtp(email=email, code_hash=h, expires_at=exp))
    db.commit()
    email_sent = send_otp_email(email, code)
    if email_sent:
        msg = "Verification code sent to your email. Continue to the next step and enter the 6-digit code."
        dev = code if settings.show_otp_in_dev else None
    else:
        msg = (
            "Email could not be sent. Check Gmail SMTP settings and try again."
        )
        dev = code if settings.show_otp_in_dev else None
    return SendOtpResponse(message=msg, email_sent=email_sent, dev_otp=dev)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="Email already registered")
    row = db.get(RegistrationOtp, email)
    now = datetime.utcnow()
    if not row or row.expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code. Request a new code.")
    if row.code_hash != hash_otp(email, payload.otp):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    user = User(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        age=payload.age,
        weight_kg=payload.weight_kg,
        height_cm=payload.height_cm,
        medical_history=payload.medical_history,
    )
    db.delete(row)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(subject=user.email, user_id=user.id, role=user.role)
    return Token(access_token=token)


@router.post("/forgot-password/send-otp", response_model=SendOtpResponse)
def forgot_password_send_otp(payload: SendOtpRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="No account found for that email")
    code = generate_otp_digits()
    row = db.get(PasswordResetOtp, email)
    expires_at = otp_expires_at()
    code_hash = hash_otp(email, code)
    if row:
        row.code_hash = code_hash
        row.expires_at = expires_at
    else:
        db.add(PasswordResetOtp(email=email, code_hash=code_hash, expires_at=expires_at))
    db.commit()
    email_sent = send_otp_email(
        email,
        code,
        subject="Your password reset code - AI Medical Assistant",
        intro="Your AI Medical Assistant password reset code is:",
        action_note="If you did not request a password reset, ignore this email.",
    )
    if email_sent:
        return SendOtpResponse(
            message="Password reset code sent to your email. Enter the 6-digit OTP to continue.",
            email_sent=True,
            dev_otp=code if settings.show_otp_in_dev else None,
        )
    return SendOtpResponse(
        message="Email could not be sent. Check Gmail SMTP settings and try again.",
        email_sent=False,
        dev_otp=code if settings.show_otp_in_dev else None,
    )


@router.post("/forgot-password/verify-otp", response_model=MessageResponse)
def forgot_password_verify_otp(payload: PasswordResetVerifyRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    row = db.get(PasswordResetOtp, email)
    now = datetime.utcnow()
    if not row or row.expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code. Request a new code.")
    if row.code_hash != hash_otp(email, payload.otp):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    return MessageResponse(message="OTP verified. You can now set a new password.")


@router.post("/forgot-password/reset", response_model=MessageResponse)
def forgot_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="No account found for that email")
    row = db.get(PasswordResetOtp, email)
    now = datetime.utcnow()
    if not row or row.expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code. Request a new code.")
    if row.code_hash != hash_otp(email, payload.otp):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.delete(row)
    db.commit()
    return MessageResponse(message="Password reset successful. Please sign in with your new password.")


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(current, k, v)
    db.add(current)
    db.commit()
    db.refresh(current)
    return current
