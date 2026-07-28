"""
GET /visualizations -- extra chart data beyond the core /analyze response:
anomaly scatter plot points, spending-by-day-of-month heatmap, monthly
cash flow (income vs expense), and top merchants.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.auth import get_current_user_id
from app.analytics.visualizations import (
    get_anomaly_scatter_data,
    get_calendar_heatmap_data,
    get_monthly_cash_flow,
    get_top_merchants,
)

router = APIRouter()


@router.get("/visualizations")
def visualizations(user_id: uuid.UUID = Depends(get_current_user_id)):
    session: Session = SessionLocal()
    try:
        return {
            "anomaly_scatter": get_anomaly_scatter_data(session, user_id),
            "calendar_heatmap": get_calendar_heatmap_data(session, user_id),
            "cash_flow": get_monthly_cash_flow(session, user_id),
            "top_merchants": get_top_merchants(session, user_id),
        }
    finally:
        session.close()
