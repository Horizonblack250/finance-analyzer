import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def _parse_transaction_date(date_str: str) -> datetime:
    for fmt in ("%d-%m-%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str}")


def get_monthly_category_trends(session: Session, user_id: uuid.UUID) -> dict:
    transactions = session.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    ).scalars().all()

    trends: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for txn in transactions:
        if float(txn.debit) == 0:
            continue
        date = _parse_transaction_date(txn.transaction_date)
        month_key = date.strftime("%Y-%m")
        trends[month_key][txn.category] += float(txn.debit)

    return {month: dict(categories) for month, categories in sorted(trends.items())}


def get_month_over_month_change(session: Session, user_id: uuid.UUID) -> dict:
    trends = get_monthly_category_trends(session, user_id)
    months = sorted(trends.keys())

    current_month_key = datetime.utcnow().strftime("%Y-%m")
    complete_months = [m for m in months if m != current_month_key]

    if len(complete_months) < 2:
        return {}

    latest_month = complete_months[-1]
    prior_months = complete_months[:-1]

    all_categories = set()
    for month_data in trends.values():
        all_categories.update(month_data.keys())

    result = {}
    for category in all_categories:
        latest_value = trends[latest_month].get(category, 0.0)
        prior_values = [trends[m].get(category, 0.0) for m in prior_months]
        prior_average = sum(prior_values) / len(prior_values) if prior_values else 0.0

        if prior_average > 0:
            pct_change = ((latest_value - prior_average) / prior_average) * 100
        else:
            pct_change = 0.0 if latest_value == 0 else 100.0

        result[category] = {
            "latest": round(latest_value, 2),
            "prior_average": round(prior_average, 2),
            "pct_change": round(pct_change, 1),
        }

    return result
