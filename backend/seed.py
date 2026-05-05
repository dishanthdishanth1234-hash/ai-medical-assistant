"""Seed reference doctors once (idempotent)."""
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import settings
from models.orm import Doctor
from security import hash_password
from services.app_settings import ensure_app_settings_defaults
from models.orm import User

log = logging.getLogger(__name__)

SEED_DOCTORS = [
    {
        "name": "Dr. Ananya Sharma",
        "specialization": "Cardiology",
        "experience_years": 12,
        "photo_url": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=400&h=400&fit=crop",
    },
    {
        "name": "Dr. James Okonkwo",
        "specialization": "General Medicine",
        "experience_years": 8,
        "photo_url": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=400&h=400&fit=crop",
    },
    {
        "name": "Dr. Maria Santos",
        "specialization": "Dermatology",
        "experience_years": 15,
        "photo_url": "https://images.unsplash.com/photo-1594824476967-48c8b964273f?w=400&h=400&fit=crop",
    },
    {
        "name": "Dr. Priya Nair",
        "specialization": "Pediatrics",
        "experience_years": 10,
        "photo_url": "https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=400&h=400&fit=crop",
    },
    {
        "name": "Dr. Daniel Kim",
        "specialization": "Orthopedics",
        "experience_years": 14,
        "photo_url": "https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=400&h=400&fit=crop",
    },
]


def seed_doctors_if_empty(db: Session) -> None:
    n = db.scalar(select(func.count()).select_from(Doctor)) or 0
    if n > 0:
        return
    for row in SEED_DOCTORS:
        db.add(Doctor(**row))
    db.commit()
    log.info("Seeded %s doctors", len(SEED_DOCTORS))


def seed_runtime_defaults(db: Session) -> None:
    ensure_app_settings_defaults(db)
    email = (settings.admin_seed_email or "").strip().lower()
    password = settings.admin_seed_password or ""
    if not email or not password:
        return
    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.name = settings.admin_seed_name or user.name
        user.password_hash = hash_password(password)
        user.role = "admin"
        db.add(user)
        db.commit()
        log.info("Updated admin user %s", email)
        return
    db.add(
        User(
            name=settings.admin_seed_name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
        )
    )
    db.commit()
    log.info("Seeded admin user %s", email)
