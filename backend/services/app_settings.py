"""Helpers for runtime application settings stored in the database."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.orm import AppSettings, NearbyHospital

DEFAULT_FOOTER = (
    "This application does not provide medical diagnosis or treatment. "
    "Always consult a licensed healthcare professional for medical decisions, "
    "emergencies, or medication changes."
)

DEFAULT_HOSPITALS = [
    {
        "name": "Kasturba Medical Hospital (KMC)",
        "address": "KMC Hospital, Attavar, Mangaluru, Karnataka 575001",
        "phone": "0824 228 5000",
        "website": "https://www.manipalhospitals.com/mangalore/",
    },
    {
        "name": "Life Care Diagnostic and Health Center",
        "address": "Noor Vista, Nawayath Colony, Jali Road, Bhatkal, Uttara Kannada, Karnataka 581320",
        "phone": "08385 992233",
        "website": "",
    },
    {
        "name": "St Ignatius Hospital",
        "address": "Prabhat Nagar, Honavar, Karnataka 581334",
        "phone": "08387 220345",
        "website": "",
    },
]


def ensure_app_settings_defaults(db: Session) -> AppSettings:
    row = db.get(AppSettings, 1)
    if not row:
        row = AppSettings(
            id=1,
            api_key=(settings.openai_api_key or "").strip() or None,
            emergency_number="112",
            footer_text=DEFAULT_FOOTER,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    if not db.scalar(select(NearbyHospital.id).limit(1)):
        for hospital in DEFAULT_HOSPITALS:
            db.add(NearbyHospital(**hospital))
        db.commit()
    return row


def get_runtime_settings(db: Session) -> AppSettings:
    return ensure_app_settings_defaults(db)


def get_runtime_api_key() -> str:
    with SessionLocal() as db:
        row = db.get(AppSettings, 1)
        if row and row.api_key:
            return row.api_key.strip()
    return (settings.openai_api_key or "").strip()
