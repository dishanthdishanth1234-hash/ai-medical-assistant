"""Purge aged user activity so health data does not persist indefinitely on the server."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from config import settings
from models.orm import (
    Appointment,
    ChatHistory,
    HealthRecord,
    MedicalReport,
    PasswordResetOtp,
    RegistrationOtp,
    User,
)

log = logging.getLogger(__name__)


def retention_cutoff() -> datetime:
    hours = max(1, int(settings.user_data_retention_hours))
    return datetime.utcnow() - timedelta(hours=hours)


def purge_expired_data(db: Session) -> dict[str, int]:
    """Delete user activity older than the configured retention window."""
    cutoff = retention_cutoff()
    counts: dict[str, int] = {}

    chat_rows = db.scalars(select(ChatHistory).where(ChatHistory.created_at < cutoff)).all()
    counts["chat_history"] = len(chat_rows)
    for row in chat_rows:
        db.delete(row)

    health_rows = db.scalars(select(HealthRecord).where(HealthRecord.created_at < cutoff)).all()
    counts["health_records"] = len(health_rows)
    for row in health_rows:
        db.delete(row)

    appt_rows = db.scalars(select(Appointment).where(Appointment.created_at < cutoff)).all()
    counts["appointments"] = len(appt_rows)
    for row in appt_rows:
        db.delete(row)

    report_rows = db.scalars(select(MedicalReport).where(MedicalReport.created_at < cutoff)).all()
    counts["medical_reports"] = len(report_rows)
    for row in report_rows:
        path = Path(row.file_path)
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                log.warning("Could not delete report file %s", path)
        db.delete(row)

    now = datetime.utcnow()
    otp_reg = db.scalars(select(RegistrationOtp).where(RegistrationOtp.expires_at < now)).all()
    otp_reset = db.scalars(select(PasswordResetOtp).where(PasswordResetOtp.expires_at < now)).all()
    counts["registration_otps"] = len(otp_reg)
    counts["password_reset_otps"] = len(otp_reset)
    for row in otp_reg:
        db.delete(row)
    for row in otp_reset:
        db.delete(row)

    # Clear optional profile health fields when there is no recent health data left.
    users = db.scalars(select(User)).all()
    profile_cleared = 0
    for user in users:
        recent_health = db.scalar(
            select(HealthRecord.id)
            .where(HealthRecord.user_id == user.id, HealthRecord.created_at >= cutoff)
            .limit(1)
        )
        if recent_health:
            continue
        if user.age is None and user.weight_kg is None and user.height_cm is None and not user.medical_history:
            continue
        user.age = None
        user.weight_kg = None
        user.height_cm = None
        user.medical_history = None
        db.add(user)
        profile_cleared += 1
    counts["profiles_cleared"] = profile_cleared

    db.commit()
    total = sum(v for k, v in counts.items() if k != "profiles_cleared")
    if total or profile_cleared:
        log.info("Data retention purge (cutoff %s): %s", cutoff.isoformat(), counts)
    return counts


def retention_notice_text() -> str:
    hours = max(1, int(settings.user_data_retention_hours))
    if hours < 24:
        window = f"{hours} hour{'s' if hours != 1 else ''}"
    elif hours % 24 == 0:
        days = hours // 24
        window = f"{days} day{'s' if days != 1 else ''}"
    else:
        window = f"{hours} hours"
    return (
        f"Privacy: chats, symptom checks, health logs, appointments, and PDF reports are removed "
        f"from the server after about {window}. Only your login account remains."
    )
