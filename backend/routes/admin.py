"""Admin dashboard APIs and safe public app configuration."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from database import get_db
from deps import get_current_admin
from models.orm import AppSettings, Appointment, Doctor, MedicalReport, NearbyHospital, User
from models.schemas import (
    AdminAppointmentOut,
    AdminAppointmentUpdate,
    AdminDashboardStats,
    AdminReportOut,
    AdminSettingsOut,
    AdminSettingsUpdate,
    AdminUserUpdate,
    DoctorCreate,
    DoctorOut,
    DoctorUpdate,
    NearbyHospitalCreate,
    NearbyHospitalOut,
    NearbyHospitalUpdate,
    PublicAppConfig,
    UserOut,
)
from services.app_settings import get_runtime_settings

router = APIRouter(tags=["admin"])
admin_router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


def _to_admin_appointment_out(row: Appointment) -> AdminAppointmentOut:
    return AdminAppointmentOut(
        id=row.id,
        user_id=row.user_id,
        user_name=row.user.name,
        user_email=row.user.email,
        doctor_id=row.doctor_id,
        doctor_name=row.doctor.name,
        specialization=row.doctor.specialization,
        appt_date=row.appt_date,
        appt_time=row.appt_time,
        notes=row.notes,
        status=row.status,
        created_at=row.created_at,
    )


def _to_admin_report_out(row: MedicalReport) -> AdminReportOut:
    return AdminReportOut(
        id=row.id,
        user_id=row.user_id,
        user_name=row.user.name,
        user_email=row.user.email,
        filename=row.filename,
        report_type=row.report_type,
        created_at=row.created_at,
    )


@router.get("/public/app-config", response_model=PublicAppConfig)
def public_app_config(db: Session = Depends(get_db)):
    app_settings = get_runtime_settings(db)
    hospitals = db.scalars(select(NearbyHospital).order_by(NearbyHospital.name.asc())).all()
    return PublicAppConfig(
        emergency_number=app_settings.emergency_number,
        footer_text=app_settings.footer_text,
        hospitals=hospitals,
    )


@admin_router.get("/dashboard/stats", response_model=AdminDashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    return AdminDashboardStats(
        total_users=db.scalar(select(func.count()).select_from(User)) or 0,
        total_doctors=db.scalar(select(func.count()).select_from(Doctor)) or 0,
        total_appointments=db.scalar(select(func.count()).select_from(Appointment)) or 0,
    )


@admin_router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.created_at.desc())).all()


@admin_router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: AdminUserUpdate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@admin_router.get("/doctors", response_model=list[DoctorOut])
def admin_list_doctors(db: Session = Depends(get_db)):
    return db.scalars(select(Doctor).order_by(Doctor.id.desc())).all()


@admin_router.post("/doctors", response_model=DoctorOut, status_code=status.HTTP_201_CREATED)
def create_doctor(payload: DoctorCreate, db: Session = Depends(get_db)):
    row = Doctor(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@admin_router.patch("/doctors/{doctor_id}", response_model=DoctorOut)
def update_doctor(doctor_id: int, payload: DoctorUpdate, db: Session = Depends(get_db)):
    row = db.get(Doctor, doctor_id)
    if not row:
        raise HTTPException(status_code=404, detail="Doctor not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@admin_router.delete("/doctors/{doctor_id}")
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    row = db.get(Doctor, doctor_id)
    if not row:
        raise HTTPException(status_code=404, detail="Doctor not found")
    in_use = db.scalar(select(func.count()).select_from(Appointment).where(Appointment.doctor_id == doctor_id)) or 0
    if in_use:
        raise HTTPException(status_code=400, detail="Doctor has appointments and cannot be removed")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("/appointments", response_model=list[AdminAppointmentOut])
def admin_list_appointments(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Appointment)
        .options(joinedload(Appointment.user), joinedload(Appointment.doctor))
        .order_by(Appointment.appt_date.desc(), Appointment.appt_time.desc(), Appointment.created_at.desc())
    ).all()
    return [_to_admin_appointment_out(row) for row in rows]


@admin_router.patch("/appointments/{appointment_id}", response_model=AdminAppointmentOut)
def admin_update_appointment(
    appointment_id: int, payload: AdminAppointmentUpdate, db: Session = Depends(get_db)
):
    row = db.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(joinedload(Appointment.user), joinedload(Appointment.doctor))
    )
    if not row:
        raise HTTPException(status_code=404, detail="Appointment not found")
    row.status = payload.status
    db.add(row)
    db.commit()
    db.refresh(row)
    row = db.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(joinedload(Appointment.user), joinedload(Appointment.doctor))
    )
    return _to_admin_appointment_out(row)


@admin_router.get("/hospitals", response_model=list[NearbyHospitalOut])
def list_hospitals(db: Session = Depends(get_db)):
    return db.scalars(select(NearbyHospital).order_by(NearbyHospital.name.asc())).all()


@admin_router.post("/hospitals", response_model=NearbyHospitalOut, status_code=status.HTTP_201_CREATED)
def create_hospital(payload: NearbyHospitalCreate, db: Session = Depends(get_db)):
    row = NearbyHospital(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@admin_router.patch("/hospitals/{hospital_id}", response_model=NearbyHospitalOut)
def update_hospital(hospital_id: int, payload: NearbyHospitalUpdate, db: Session = Depends(get_db)):
    row = db.get(NearbyHospital, hospital_id)
    if not row:
        raise HTTPException(status_code=404, detail="Hospital not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@admin_router.delete("/hospitals/{hospital_id}")
def delete_hospital(hospital_id: int, db: Session = Depends(get_db)):
    row = db.get(NearbyHospital, hospital_id)
    if not row:
        raise HTTPException(status_code=404, detail="Hospital not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("/settings", response_model=AdminSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    row = get_runtime_settings(db)
    return AdminSettingsOut(
        api_key=row.api_key or "",
        emergency_number=row.emergency_number,
        footer_text=row.footer_text,
    )


@admin_router.patch("/settings", response_model=AdminSettingsOut)
def update_settings(payload: AdminSettingsUpdate, db: Session = Depends(get_db)):
    row = get_runtime_settings(db)
    row.api_key = (payload.api_key or "").strip() or None
    row.emergency_number = payload.emergency_number.strip()
    row.footer_text = payload.footer_text.strip()
    db.add(row)
    db.commit()
    db.refresh(row)
    return AdminSettingsOut(
        api_key=row.api_key or "",
        emergency_number=row.emergency_number,
        footer_text=row.footer_text,
    )


@admin_router.get("/reports", response_model=list[AdminReportOut])
def list_reports(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(MedicalReport)
        .options(joinedload(MedicalReport.user))
        .order_by(MedicalReport.created_at.desc())
    ).all()
    return [_to_admin_report_out(row) for row in rows]


@admin_router.get("/reports/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    row = db.scalar(select(MedicalReport).where(MedicalReport.id == report_id))
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path(row.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report file is missing")
    return FileResponse(path=str(path), media_type="application/pdf", filename=row.filename)


router.include_router(admin_router)
