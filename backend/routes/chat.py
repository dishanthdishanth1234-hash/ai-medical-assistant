"""AI chat and doctor chat: stores exchanges in MySQL."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models.orm import ChatHistory, Doctor, User
from models.schemas import ChatHistoryItem, ChatRequest, ChatResponse, DoctorChatRequest, DoctorChatResponse
from services.ai_service import generate_doctor_intro, generate_doctor_reply, generate_reply

router = APIRouter(tags=["chat"])


def _doctor_chat_marker(doctor_id: int) -> str:
    return f"[DoctorChat:{doctor_id}]"


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    try:
        reply = generate_reply(payload.message, mode="chat")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant temporarily unavailable. Try again shortly.",
        )
    row = ChatHistory(user_id=current.id, message=payload.message, response=reply)
    db.add(row)
    db.commit()
    return ChatResponse(response=reply)


@router.get("/chat/history", response_model=list[ChatHistoryItem])
def chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 200))
    rows = db.scalars(
        select(ChatHistory)
        .where(ChatHistory.user_id == current.id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


@router.post("/doctor-chat/start/{doctor_id}", response_model=DoctorChatResponse)
def doctor_chat_start(
    doctor_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    intro = generate_doctor_intro(doctor.name, doctor.specialization)
    marker = _doctor_chat_marker(doctor_id)
    existing = db.scalar(
        select(ChatHistory)
        .where(ChatHistory.user_id == current.id, ChatHistory.message == f"{marker} __intro__")
        .order_by(ChatHistory.created_at.desc())
    )
    if not existing:
        db.add(ChatHistory(user_id=current.id, message=f"{marker} __intro__", response=intro))
        db.commit()
    return DoctorChatResponse(doctor_name=doctor.name, specialization=doctor.specialization, response=intro)


@router.post("/doctor-chat", response_model=DoctorChatResponse)
def doctor_chat(
    payload: DoctorChatRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    doctor = db.get(Doctor, payload.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    try:
        reply = generate_doctor_reply(doctor.name, doctor.specialization, payload.message)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Doctor chat temporarily unavailable. Try again shortly.",
        )
    marker = _doctor_chat_marker(payload.doctor_id)
    row = ChatHistory(user_id=current.id, message=f"{marker} {payload.message}", response=reply)
    db.add(row)
    db.commit()
    return DoctorChatResponse(doctor_name=doctor.name, specialization=doctor.specialization, response=reply)


@router.get("/doctor-chat/history/{doctor_id}", response_model=list[ChatHistoryItem])
def doctor_chat_history(
    doctor_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 200))
    marker = _doctor_chat_marker(doctor_id)
    rows = db.scalars(
        select(ChatHistory)
        .where(ChatHistory.user_id == current.id, ChatHistory.message.like(f"{marker}%"))
        .order_by(ChatHistory.created_at.asc())
        .limit(limit)
    ).all()
    return list(rows)
