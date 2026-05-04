"""Structured diet / wellness guidance."""
from fastapi import APIRouter, Depends

from deps import get_current_user
from models.orm import User
from models.schemas import DietPlanResponse
from services.diet_plan import get_diet_plan

router = APIRouter(prefix="/diet-plan", tags=["diet"])


@router.get("", response_model=DietPlanResponse)
def diet_plan(current: User = Depends(get_current_user)):
    data = get_diet_plan()
    return DietPlanResponse(**data)
