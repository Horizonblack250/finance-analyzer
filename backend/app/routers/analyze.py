"""
GET /analyze -- returns everything the analytics engine knows: monthly
trends, month-over-month changes, recurring payments, next-month forecast,
and detected anomalies, all in one response. A real frontend dashboard
will likely want all of this on a single page load rather than four
separate requests.
"""

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.analytics.trends import get_monthly_category_trends, get_month_over_month_change
from app.analytics.recurring import detect_recurring_payments
from app.analytics.forecasting import forecast_next_month
from app.analytics.anomalies import detect_anomalies

router = APIRouter()


@router.get("/analyze")
def analyze():
    session: Session = SessionLocal()
    try:
        return {
            "monthly_trends": get_monthly_category_trends(session, DEFAULT_USER_ID),
            "month_over_month_change": get_month_over_month_change(session, DEFAULT_USER_ID),
            "recurring_payments": detect_recurring_payments(session, DEFAULT_USER_ID),
            "forecast_next_month": forecast_next_month(session, DEFAULT_USER_ID),
            "anomalies": detect_anomalies(session, DEFAULT_USER_ID),
        }
    finally:
        session.close()
