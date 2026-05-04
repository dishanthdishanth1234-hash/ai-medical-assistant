"""Pydantic request/response schemas for API validation."""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class SendOtpRequest(BaseModel):
    email: EmailStr


class SendOtpResponse(BaseModel):
    message: str
    email_sent: bool = False
    # Returned when email could not be sent (no SMTP / failure), or when SHOW_OTP_IN_DEV=true
    dev_otp: Optional[str] = None


class PasswordResetVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

    @field_validator("otp")
    @classmethod
    def strip_reset_otp(cls, v: str) -> str:
        return v.strip()


class PasswordResetRequest(PasswordResetVerifyRequest):
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    age: Optional[int] = Field(default=None, ge=0, le=130)
    weight_kg: Optional[float] = Field(default=None, ge=1, le=500)
    height_cm: Optional[float] = Field(default=None, ge=50, le=280)
    medical_history: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("otp")
    @classmethod
    def strip_otp(cls, v: str) -> str:
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    age: Optional[int] = Field(default=None, ge=0, le=130)
    weight_kg: Optional[float] = Field(default=None, ge=1, le=500)
    height_cm: Optional[float] = Field(default=None, ge=50, le=280)
    medical_history: Optional[str] = Field(default=None, max_length=4000)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str
    age: Optional[int]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    medical_history: Optional[str]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    response: str


class DoctorChatRequest(BaseModel):
    doctor_id: int = Field(ge=1)
    message: str = Field(min_length=1, max_length=4000)


class DoctorChatResponse(BaseModel):
    doctor_name: str
    specialization: str
    response: str


class SymptomRequest(BaseModel):
    """Single symptom only (one word or short phrase)."""

    symptom: str = Field(min_length=2, max_length=120)

    @field_validator("symptom")
    @classmethod
    def one_symptom(cls, v: str) -> str:
        s = " ".join(v.strip().split())
        if "," in s or ";" in s:
            raise ValueError("Enter only one symptom (no commas or lists).")
        return s


class SymptomStructuredResponse(BaseModel):
    condition: str
    doctor_type: str
    precautions: List[str]
    disclaimer: str


class HealthReportPdfRequest(SymptomStructuredResponse):
    """Symptom snapshot from the checker; diet plan is merged on the server for the PDF."""

    symptom: str = Field(min_length=2, max_length=120)

    @field_validator("symptom")
    @classmethod
    def one_symptom_pdf(cls, v: str) -> str:
        s = " ".join(v.strip().split())
        if "," in s or ";" in s:
            raise ValueError("Enter only one symptom (no commas or lists).")
        return s


class HealthRecordCreate(BaseModel):
    weight_kg: float = Field(ge=1, le=500)
    height_cm: float = Field(ge=50, le=280)
    recorded_date: Optional[date] = None


class HealthRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bmi: float
    weight_kg: float
    recorded_date: date
    created_at: datetime


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    response: str
    created_at: datetime


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    specialization: str
    experience_years: int
    photo_url: str


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(ge=1)
    appt_date: date
    appt_time: str = Field(min_length=4, max_length=8)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("appt_time")
    @classmethod
    def normalize_time(cls, v: str) -> str:
        v = v.strip()
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be HH:MM (24h)")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Invalid time")
        return f"{h:02d}:{m:02d}"


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    doctor_name: str
    specialization: str
    appt_date: date
    appt_time: str
    notes: Optional[str]
    status: str
    created_at: datetime


class DietPlanResponse(BaseModel):
    recommended_foods: List[str]
    foods_to_avoid: List[str]
    healthy_habits: List[str]
    disclaimer: str


class AdminUserUpdate(BaseModel):
    role: str = Field(pattern=r"^(user|admin)$")


class DoctorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    specialization: str = Field(min_length=2, max_length=180)
    experience_years: int = Field(ge=0, le=80)
    photo_url: str = Field(min_length=4, max_length=512)


class DoctorUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    specialization: Optional[str] = Field(default=None, min_length=2, max_length=180)
    experience_years: Optional[int] = Field(default=None, ge=0, le=80)
    photo_url: Optional[str] = Field(default=None, min_length=4, max_length=512)


class AdminAppointmentOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: EmailStr
    doctor_id: int
    doctor_name: str
    specialization: str
    appt_date: date
    appt_time: str
    notes: Optional[str]
    status: str
    created_at: datetime


class AdminAppointmentUpdate(BaseModel):
    status: str = Field(pattern=r"^(scheduled|confirmed|completed|cancelled|rescheduled)$")


class NearbyHospitalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    address: str = Field(min_length=5, max_length=255)
    phone: str = Field(min_length=5, max_length=40)
    website: Optional[str] = Field(default=None, max_length=255)


class NearbyHospitalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    phone: str
    website: Optional[str]


class NearbyHospitalUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    address: Optional[str] = Field(default=None, min_length=5, max_length=255)
    phone: Optional[str] = Field(default=None, min_length=5, max_length=40)
    website: Optional[str] = Field(default=None, max_length=255)


class AdminSettingsUpdate(BaseModel):
    api_key: Optional[str] = Field(default=None, max_length=255)
    emergency_number: str = Field(min_length=2, max_length=40)
    footer_text: str = Field(min_length=10, max_length=4000)


class AdminSettingsOut(BaseModel):
    api_key: str
    emergency_number: str
    footer_text: str


class PublicAppConfig(BaseModel):
    emergency_number: str
    footer_text: str
    hospitals: List[NearbyHospitalOut]


class AdminDashboardStats(BaseModel):
    total_users: int
    total_doctors: int
    total_appointments: int


class AdminReportOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: EmailStr
    filename: str
    report_type: str
    created_at: datetime
