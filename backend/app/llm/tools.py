"""
Tool schemas the LLM sees, and the Python functions that actually execute
them. Every executor takes (session, user_id, **kwargs) and returns a
JSON-serializable dict -- the LLM decides WHICH of these to call, based on
the user's question, and never sees raw transaction rows, only these
pre-computed summaries.

NOTE: forecast and top-merchants tools aren't wired in yet -- need to see
forecasting.py / visualizations.py to match function signatures exactly
rather than guessing. Fast-follow once those are shared.
"""

import uuid

from sqlalchemy.orm import Session

from app.analytics.trends import get_monthly_category_trends, get_month_over_month_change
from app.analytics.anomalies import detect_anomalies
from app.analytics.recurring import detect_recurring_payments
from app.analytics.budget import calculate_budget_outlook, generate_recommendations


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_monthly_trends",
            "description": (
                "Get total spending per category, broken down by month. Use "
                "this for questions about spending over time, comparisons "
                "between months, or which categories cost the most."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_month_over_month_change",
            "description": (
                "Get percent change in spending per category between the "
                "most recent complete month and the prior average. Use this "
                "for 'why did my spending jump' or 'what changed recently' "
                "questions."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_anomalies",
            "description": (
                "Get transactions flagged as unusual by the anomaly "
                "detection model, each with merchant, amount, category, and "
                "anomaly score. Use for questions about unusual or one-off "
                "spending."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recurring_payments",
            "description": (
                "Get transactions identified as recurring subscriptions/"
                "bills based on consistent amount and interval."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget_outlook",
            "description": (
                "Get monthly income, forecasted total spend, predicted "
                "surplus/shortfall, and rule-based recommendations. Use for "
                "questions about being on track, over budget, or saving "
                "money."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _get_monthly_trends(session: Session, user_id: uuid.UUID, **_) -> dict:
    return get_monthly_category_trends(session, user_id)


def _get_month_over_month_change(session: Session, user_id: uuid.UUID, **_) -> dict:
    return get_month_over_month_change(session, user_id)


def _get_anomalies(session: Session, user_id: uuid.UUID, **_) -> dict:
    return {"anomalies": detect_anomalies(session, user_id)}


def _get_recurring_payments(session: Session, user_id: uuid.UUID, **_) -> dict:
    return {"recurring": detect_recurring_payments(session, user_id)}


def _get_budget_outlook(session: Session, user_id: uuid.UUID, **_) -> dict:
    outlook = calculate_budget_outlook(session, user_id)
    recommendations = generate_recommendations(session, user_id)
    return {**outlook, "recommendations": recommendations}


TOOL_FUNCTIONS = {
    "get_monthly_trends": _get_monthly_trends,
    "get_month_over_month_change": _get_month_over_month_change,
    "get_anomalies": _get_anomalies,
    "get_recurring_payments": _get_recurring_payments,
    "get_budget_outlook": _get_budget_outlook,
}