"""
GET /analyze -- returns everything the analytics engine knows for the
LOGGED-IN USER: monthly trends, month-over-month changes, recurring
payments, next-month forecast, and detected anomalies.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.auth import get_current_user_id
from app.analytics.trends import get_monthly_category_trends, get_month_over_month_change
from app.analytics.recurring import detect_recurring_payments
from app.analytics.forecasting import forecast_next_month
from app.analytics.anomalies import detect_anomalies

router = APIRouter()


@router.get("/analyze")
def analyze(user_id: uuid.UUID = Depends(get_current_user_id)):
    session: Session = SessionLocal()
    try:
        return {
            "monthly_trends": get_monthly_category_trends(session, user_id),
            "month_over_month_change": get_month_over_month_change(session, user_id),
            "recurring_payments": detect_recurring_payments(session, user_id),
            "forecast_next_month": forecast_next_month(session, user_id),
            "anomalies": detect_anomalies(session, user_id),
        }
    finally:
        session.close()
