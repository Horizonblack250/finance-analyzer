"""
Budget outlook: compares next month's forecasted total spend against the
user's self-reported income, and generates rule-based optimization
suggestions.

Design notes (consistent with earlier research-informed choices in this
project):
- Recommendations are framed against the user's OWN historical baseline
  ("trending above your average"), not a countdown-style "you have X left"
  number -- the research flagged that framing as something that can
  backfire and encourage MORE spending near the end of a budget period.
- Only "discretionary" categories are targeted for cut-back suggestions.
  Rent, utilities, and person-to-person transfers aren't things you can
  meaningfully "optimize" the way a food delivery habit is.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_budget import UserBudget
from app.analytics.trends import get_month_over_month_change
from app.analytics.forecasting import forecast_next_month

# Categories where "spend less" is a meaningful, actionable suggestion.
# Deliberately excludes fixed obligations (rent, utilities) and transfers,
# since those aren't really "optimizable" the way a discretionary habit is.
DISCRETIONARY_CATEGORIES = {
    "Food Delivery", "Food & Dining", "Shopping", "Entertainment", "Snacks & Vending",
}

TREND_FLAG_THRESHOLD_PCT = 25.0  # only flag categories trending meaningfully above average
MIN_AMOUNT_TO_FLAG = 200.0  # ignore tiny categories even if their % change looks dramatic


def get_user_budget(session: Session, user_id: uuid.UUID) -> float | None:
    budget = session.execute(
        select(UserBudget).where(UserBudget.user_id == user_id)
    ).scalar_one_or_none()
    return float(budget.monthly_income) if budget else None


def set_user_budget(session: Session, user_id: uuid.UUID, monthly_income: float) -> None:
    existing = session.execute(
        select(UserBudget).where(UserBudget.user_id == user_id)
    ).scalar_one_or_none()

    if existing:
        existing.monthly_income = Decimal(str(monthly_income))
    else:
        session.add(UserBudget(user_id=user_id, monthly_income=Decimal(str(monthly_income))))
    session.commit()


def calculate_budget_outlook(session: Session, user_id: uuid.UUID) -> dict:
    """
    Returns:
        {
            "status": "no_budget_set" | "surplus" | "shortfall",
            "monthly_income": float | None,
            "total_predicted_spend": float,
            "surplus_or_shortfall": float | None,  # positive = surplus, negative = shortfall
        }
    """
    forecast = forecast_next_month(session, user_id)
    total_predicted_spend = round(sum(d["predicted"] for d in forecast.values()), 2)

    income = get_user_budget(session, user_id)
    if income is None:
        return {
            "status": "no_budget_set",
            "monthly_income": None,
            "total_predicted_spend": total_predicted_spend,
            "surplus_or_shortfall": None,
        }

    surplus_or_shortfall = round(income - total_predicted_spend, 2)
    status = "surplus" if surplus_or_shortfall >= 0 else "shortfall"

    return {
        "status": status,
        "monthly_income": income,
        "total_predicted_spend": total_predicted_spend,
        "surplus_or_shortfall": surplus_or_shortfall,
    }


def generate_recommendations(session: Session, user_id: uuid.UUID) -> list[dict]:
    """
    Rule-based optimization suggestions, e.g.:
        [{"category": "Food Delivery", "message": "...", "pct_change": 42.0}]
    """
    changes = get_month_over_month_change(session, user_id)
    forecast = forecast_next_month(session, user_id)

    candidates = []
    for category, data in changes.items():
        if category not in DISCRETIONARY_CATEGORIES:
            continue
        if data["latest"] < MIN_AMOUNT_TO_FLAG:
            continue
        if data["pct_change"] < TREND_FLAG_THRESHOLD_PCT:
            continue
        candidates.append((category, data))

    # Sort by how much money is actually at stake (not just percentage --
    # a 200% jump on a Rs.50 category matters less than a 30% jump on Rs.5000)
    candidates.sort(key=lambda c: c[1]["latest"] - c[1]["prior_average"], reverse=True)

    recommendations = []
    for category, data in candidates[:3]:
        excess = round(data["latest"] - data["prior_average"], 2)
        recommendations.append({
            "category": category,
            "pct_change": data["pct_change"],
            "latest": data["latest"],
            "prior_average": data["prior_average"],
            "message": (
                f"{category} is running {data['pct_change']:.0f}% above your usual average "
                f"this month (Rs.{data['latest']:,.0f} vs your typical Rs.{data['prior_average']:,.0f}). "
                f"Bringing it back toward your average would free up about Rs.{excess:,.0f}."
            ),
        })

    if not recommendations:
        recommendations.append({
            "category": None,
            "pct_change": None,
            "latest": None,
            "prior_average": None,
            "message": "Nothing stands out as unusually high right now -- your discretionary spending looks consistent with your normal pattern.",
        })

    return recommendations
