"""OTP generation and verification (hashed at rest)."""
import hashlib
import secrets
from datetime import datetime, timedelta

from config import settings


def generate_otp_digits(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(email: str, code: str) -> str:
    raw = f"{email.lower().strip()}:{code}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def otp_expires_at() -> datetime:
    """Naive UTC for MySQL TIMESTAMP compatibility."""
    return datetime.utcnow() + timedelta(minutes=settings.otp_expire_minutes)
