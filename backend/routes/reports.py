"""PDF health summary reports (authenticated)."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models.orm import MedicalReport, User
from models.schemas import HealthReportPdfRequest
from services.diet_plan import get_diet_plan
from services.pdf_report import build_health_report_pdf

router = APIRouter(prefix="/reports", tags=["reports"])
_REPORTS_DIR = Path(__file__).resolve().parent.parent / "generated_reports"


def _num(v) -> float | None:
    if v is None:
        return None
    return float(v)


@router.post("/health-pdf")
def health_summary_pdf(
    payload: HealthReportPdfRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    diet = get_diet_plan()
    pdf_bytes = build_health_report_pdf(
        user_name=current.name,
        user_email=current.email,
        age=current.age,
        weight_kg=_num(current.weight_kg),
        height_cm=_num(current.height_cm),
        medical_history=current.medical_history,
        symptom=payload.symptom,
        condition=payload.condition,
        doctor_type=payload.doctor_type,
        precautions=list(payload.precautions or []),
        symptom_disclaimer=payload.disclaimer,
        diet=diet,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_email = (current.email or "user").split("@")[0].replace(".", "_")[:40]
    filename = f"health_report_{safe_email}_{stamp}.pdf"
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = _REPORTS_DIR / filename
    file_path.write_bytes(pdf_bytes)
    db.add(
        MedicalReport(
            user_id=current.id,
            filename=filename,
            file_path=str(file_path),
            report_type="health_summary",
        )
    )
    db.commit()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
