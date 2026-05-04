"""List doctors for recommendations (public)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models.orm import Doctor
from models.schemas import DoctorOut

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("/", response_model=list[DoctorOut])
def list_doctors(db: Session = Depends(get_db)):
    rows = db.scalars(select(Doctor).order_by(Doctor.id)).all()
    return rows
