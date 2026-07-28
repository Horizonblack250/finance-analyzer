"""
POST /budget -- set your monthly income/budget target
GET /budget -- get your current budget outlook and optimization recommendations
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.auth import get_current_user_id
from app.analytics.budget import (
    get_user_budget,
    set_user_budget,
    calculate_budget_outlook,
    generate_recommendations,
)

router = APIRouter()


class SetBudgetRequest(BaseModel):
    monthly_income: float


@router.post("/budget")
def update_budget(
    body: SetBudgetRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    session: Session = SessionLocal()
    try:
        set_user_budget(session, user_id, body.monthly_income)
        return {"status": "saved", "monthly_income": body.monthly_income}
    finally:
        session.close()


@router.get("/budget")
def get_budget(user_id: uuid.UUID = Depends(get_current_user_id)):
    session: Session = SessionLocal()
    try:
        outlook = calculate_budget_outlook(session, user_id)
        recommendations = generate_recommendations(session, user_id)
        return {
            **outlook,
            "recommendations": recommendations,
        }
    finally:
        session.close()
