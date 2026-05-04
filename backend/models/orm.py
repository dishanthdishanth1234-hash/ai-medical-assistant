"""SQLAlchemy ORM models matching database/schema.sql."""
from datetime import date, datetime
from typing import List

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.dialects.mysql import INTEGER as MYSQL_INTEGER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

# MySQL requires FK column types to match exactly (including UNSIGNED). Plain Integer() creates signed INT.
_MysqlUInt = MYSQL_INTEGER(unsigned=True)
UserId = Integer().with_variant(_MysqlUInt, "mysql")
UserFk = Integer().with_variant(_MysqlUInt, "mysql")
DoctorId = Integer().with_variant(_MysqlUInt, "mysql")
DoctorFk = Integer().with_variant(_MysqlUInt, "mysql")
AppointmentPk = BigInteger().with_variant(MYSQL_BIGINT(unsigned=True), "mysql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(UserId, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user", server_default="user")
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    height_cm: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    medical_history: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    chats: Mapped[List["ChatHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    health_records: Mapped[List["HealthRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    appointments: Mapped[List["Appointment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reports: Mapped[List["MedicalReport"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RegistrationOtp(Base):
    __tablename__ = "registration_otps"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PasswordResetOtp(Base):
    __tablename__ = "password_reset_otps"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(DoctorId, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialization: Mapped[str] = mapped_column(String(180), nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    photo_url: Mapped[str] = mapped_column(String(512), nullable=False)

    appointments: Mapped[List["Appointment"]] = relationship(back_populates="doctor")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(AppointmentPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        type_=UserFk,
        nullable=False,
    )
    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="RESTRICT"),
        type_=DoctorFk,
        nullable=False,
    )
    appt_date: Mapped[date] = mapped_column(Date, nullable=False)
    appt_time: Mapped[str] = mapped_column(String(8), nullable=False)
    notes: Mapped[str] = mapped_column(String(500), nullable=True)  # NULL when empty
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled", server_default="scheduled"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        type_=UserFk,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="chats")


class HealthRecord(Base):
    __tablename__ = "health_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        type_=UserFk,
        nullable=False,
    )
    bmi: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="health_records")


class NearbyHospital(Base):
    __tablename__ = "nearby_hospitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    website: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_key: Mapped[str] = mapped_column(String(255), nullable=True)
    emergency_number: Mapped[str] = mapped_column(String(40), nullable=False, default="112")
    footer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "This application does not provide medical diagnosis or treatment. "
            "Always consult a licensed healthcare professional for medical decisions, "
            "emergencies, or medication changes."
        ),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        type_=UserFk,
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, default="health_summary")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="reports")
