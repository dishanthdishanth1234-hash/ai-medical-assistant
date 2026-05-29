"""Persisted appointment booking with a doctor."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database import get_db
from deps import get_current_user
from models.orm import Appointment, Doctor, User
from models.schemas import AppointmentCreate, AppointmentOut

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _to_out(a: Appointment) -> AppointmentOut:
    d = a.doctor
    return AppointmentOut(
        id=a.id,
        doctor_id=a.doctor_id,
        doctor_name=d.name,
        specialization=d.specialization,
        appt_date=a.appt_date,
        appt_time=a.appt_time,
        notes=a.notes,
        status=a.status,
        created_at=a.created_at,
    )


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    rows = db.scalars(
        select(Appointment)
        .where(Appointment.user_id == current.id)
        .options(joinedload(Appointment.doctor))
        .order_by(Appointment.appt_date.desc(), Appointment.appt_time.desc())
    ).all()
    return [_to_out(a) for a in rows]


import logging
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    doc = db.get(Doctor, payload.doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
    notes = (payload.notes or "").strip() or None
    row = Appointment(
        user_id=current.id,
        doctor_id=payload.doctor_id,
        appt_date=payload.appt_date,
        appt_time=payload.appt_time,
        notes=notes,
    )
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        row = db.scalar(
            select(Appointment)
            .where(Appointment.id == row.id)
            .options(joinedload(Appointment.doctor))
        )
        if not row:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved appointment.")
        return _to_out(row)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while booking appointment: {e}")
        raise HTTPException(status_code=500, detail=f"Database error occurred while saving the appointment: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while booking appointment: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing the appointment.")


@router.delete("/{appointment_id}")
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    row = db.get(Appointment, appointment_id)
    if not row or row.user_id != current.id:
        raise HTTPException(status_code=404, detail="Appointment not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
