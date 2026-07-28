"""
Additional visualization-focused analytics: data shaped specifically for
charts that go beyond the core trends/recurring/forecast/anomaly modules.
"""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.analytics.trends import _parse_transaction_date
from app.analytics.anomalies import _build_features, MIN_TRANSACTIONS_FOR_DETECTION
from app.analytics.recurring import detect_recurring_payments
from app.analytics.anomaly_exclusions import get_excluded_merchants, is_excluded


def get_anomaly_scatter_data(session: Session, user_id: uuid.UUID) -> list[dict]:
    """
    Returns every (non-recurring, non-excluded) debit transaction with its
    day-of-month, amount, and whether it was flagged anomalous -- this is
    literally the feature space Isolation Forest works in, so plotting it
    visualizes the model's decision surface directly, not just its output.
    """
    from app.analytics.anomalies import detect_anomalies

    transactions = list(session.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.debit > 0,
        )
    ).scalars().all())

    if len(transactions) < MIN_TRANSACTIONS_FOR_DETECTION:
        return []

    recurring_merchants = {r["merchant"] for r in detect_recurring_payments(session, user_id)}
    excluded_merchants = get_excluded_merchants(session, user_id)
    filtered = [
        t for t in transactions
        if t.clean_merchant not in recurring_merchants
        and not is_excluded(t.clean_merchant, excluded_merchants)
    ]

    if len(filtered) < MIN_TRANSACTIONS_FOR_DETECTION:
        return []

    anomalies = detect_anomalies(session, user_id)
    anomaly_keys = {(a["date"], a["merchant"], a["amount"]) for a in anomalies}

    points = []
    for t in filtered:
        date = _parse_transaction_date(t.transaction_date)
        key = (t.transaction_date, t.clean_merchant, float(t.debit))
        points.append({
            "date": t.transaction_date,
            "day_of_month": date.day,
            "amount": float(t.debit),
            "merchant": t.clean_merchant,
            "category": t.category,
            "is_anomaly": key in anomaly_keys,
        })

    return points


def get_calendar_heatmap_data(session: Session, user_id: uuid.UUID) -> dict:
    """
    Total spend aggregated by day-of-month (1-31), across all months --
    answers "which days of the month do I tend to spend the most on",
    not which specific calendar date.
    """
    transactions = session.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.debit > 0,
        )
    ).scalars().all()

    totals: dict[int, float] = defaultdict(float)
    for t in transactions:
        date = _parse_transaction_date(t.transaction_date)
        totals[date.day] += float(t.debit)

    return {str(day): round(totals.get(day, 0.0), 2) for day in range(1, 32)}


def get_monthly_cash_flow(session: Session, user_id: uuid.UUID) -> dict:
    """
    Income vs. expense per month, and the net -- a step beyond the
    spending-only trends view, showing the full picture of money in vs out.
    """
    transactions = session.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    ).scalars().all()

    flow: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})

    for t in transactions:
        date = _parse_transaction_date(t.transaction_date)
        month_key = date.strftime("%Y-%m")
        flow[month_key]["income"] += float(t.credit)
        flow[month_key]["expense"] += float(t.debit)

    result = {}
    for month, data in sorted(flow.items()):
        income = round(data["income"], 2)
        expense = round(data["expense"], 2)
        result[month] = {
            "income": income,
            "expense": expense,
            "net": round(income - expense, 2),
        }

    return result


def get_top_merchants(session: Session, user_id: uuid.UUID, limit: int = 10) -> list[dict]:
    """Top merchants by total spend (debit only)."""
    transactions = session.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.debit > 0,
        )
    ).scalars().all()

    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for t in transactions:
        totals[t.clean_merchant] += float(t.debit)
        counts[t.clean_merchant] += 1

    ranked = sorted(totals.items(), key=lambda x: -x[1])[:limit]
    return [
        {"merchant": name, "total": round(total, 2), "count": counts[name]}
        for name, total in ranked
    ]
