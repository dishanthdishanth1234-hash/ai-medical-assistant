"""Single-symptom checker → structured JSON (stored in chat_history as JSON string)."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models.orm import ChatHistory, User
from models.schemas import SymptomRequest, SymptomStructuredResponse
from services.ai_service import analyze_symptom_structured

router = APIRouter(tags=["symptoms"])


@router.post("/symptoms", response_model=SymptomStructuredResponse)
def symptoms_check(
    payload: SymptomRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    try:
        data = analyze_symptom_structured(payload.symptom)
        out = SymptomStructuredResponse(**data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Symptom analysis temporarily unavailable.",
        )
    stored = json.dumps(out.model_dump(), ensure_ascii=False)
    row = ChatHistory(
        user_id=current.id,
        message=f"[Symptom] {payload.symptom}",
        response=stored,
    )
    db.add(row)
    db.commit()
    return out
