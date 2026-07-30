"""
Answers "what date range does my data currently cover" -- deliberately
kept separate from the main /analyze endpoint, which runs the full
trends/recurring/forecast/anomaly pipeline. This just needs a quick
min/max over dates, so it stays fast and cheap to call on every page load.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.analytics.trends import _parse_transaction_date


def get_data_coverage(session: Session, user_id: uuid.UUID) -> dict:
    transactions = session.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    ).scalars().all()

    if not transactions:
        return {
            "has_data": False,
            "earliest_month": None,
            "latest_month": None,
            "months_covered": [],
            "total_transactions": 0,
        }

    dates = [_parse_transaction_date(t.transaction_date) for t in transactions]
    month_keys = sorted({d.strftime("%Y-%m") for d in dates})

    return {
        "has_data": True,
        "earliest_month": month_keys[0],
        "latest_month": month_keys[-1],
        "months_covered": month_keys,
        "total_transactions": len(transactions),
    }
