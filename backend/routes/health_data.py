"""Health records: BMI + weight history."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models.orm import HealthRecord, User
from models.schemas import HealthRecordCreate, HealthRecordOut

router = APIRouter(tags=["health"])


def _bmi(weight_kg: float, height_cm: float) -> float:
    h_m = height_cm / 100.0
    if h_m <= 0:
        raise HTTPException(status_code=400, detail="Invalid height")
    return round(weight_kg / (h_m * h_m), 2)


@router.post("/health-data", response_model=HealthRecordOut, status_code=status.HTTP_201_CREATED)
def add_health_record(
    payload: HealthRecordCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    recorded = payload.recorded_date or date.today()
    bmi = _bmi(payload.weight_kg, payload.height_cm)
    row = HealthRecord(user_id=current.id, bmi=bmi, weight_kg=payload.weight_kg, recorded_date=recorded)
    db.add(row)
    # Keep profile weight/height loosely in sync with latest entry
    current.weight_kg = payload.weight_kg
    current.height_cm = payload.height_cm
    db.add(current)
    db.commit()
    db.refresh(row)
    return row


@router.get("/health-data", response_model=list[HealthRecordOut])
def list_health_records(
    limit: int = 100,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 365))
    rows = db.scalars(
        select(HealthRecord)
        .where(HealthRecord.user_id == current.id)
        .order_by(HealthRecord.recorded_date.desc(), HealthRecord.id.desc())
        .limit(limit)
    ).all()
    return rows
