"""
Monthly spending trends: aggregates transactions by month and category,
so we can answer "how did my spending change over time" -- the core of
the "12 months consolidated analysis" feature from the original project
goal.

Design note: this works directly off whatever's in the database for a
given user, regardless of which statement/month it came from -- so as
more statements get imported, trends automatically extend to cover them.
"""

import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def _parse_transaction_date(date_str: str) -> datetime:
    """
    Transaction dates are stored as strings in their original source format
    (DD-MM-YY for relationship_summary statements, DD/MM/YYYY for
    statement_of_account ones) -- we need to handle both when grouping by month.
    """
    for fmt in ("%d-%m-%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str}")


def get_monthly_category_trends(session: Session, user_id: uuid.UUID) -> dict:
    """
    Returns spending (debits only) grouped by year-month and category, e.g.:
        {
            "2026-04": {"Food Delivery": 1200.50, "Transport": 340.00, ...},
            "2026-05": {"Food Delivery": 980.25, ...},
        }
    """
    transactions = session.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    ).scalars().all()

    trends: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for txn in transactions:
        if float(txn.debit) == 0:
            continue  # only track spending, not incoming credits, in trends
        date = _parse_transaction_date(txn.transaction_date)
        month_key = date.strftime("%Y-%m")
        trends[month_key][txn.category] += float(txn.debit)

    # Convert nested defaultdicts to plain dicts for clean output/serialization
    return {month: dict(categories) for month, categories in sorted(trends.items())}


def get_month_over_month_change(session: Session, user_id: uuid.UUID) -> dict:
    """
    For each category, compares the most recent COMPLETE month's spending
    to the average of all prior months -- this is the "historical baseline"
    comparison the research flagged as the RIGHT framing (vs. a fixed
    budget-remaining number, which the research showed can backfire).

    The current, still-in-progress month is deliberately EXCLUDED from being
    treated as "latest": comparing a partial month (e.g. 5 days into July)
    against full prior months makes every category look like it crashed,
    which is a comparison artifact, not a real trend. We only compare
    complete months against each other.

    Returns:
        {
            "Food Delivery": {"latest": 980.25, "prior_average": 1100.00, "pct_change": -10.9},
            ...
        }
    """
    trends = get_monthly_category_trends(session, user_id)
    months = sorted(trends.keys())

    current_month_key = datetime.utcnow().strftime("%Y-%m")
    complete_months = [m for m in months if m != current_month_key]

    if len(complete_months) < 2:
        return {}  # not enough complete-month history to compare yet

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
