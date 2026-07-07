"""
Recurring payment detection.

Design (informed by the research notes from earlier in this project):
- Real recurring payments (rent, subscriptions) have BOTH a consistent
  amount AND a consistent interval between occurrences.
- Frequent habitual purchases (daily/weekly food delivery, cab rides) can
  LOOK recurring just because they're frequent, but their amount and/or
  interval varies too much to be a real "recurring bill" -- Plaid's
  production system explicitly excludes these, and we do the same here.
- We deliberately only flag something recurring if the average interval is
  at least ~20 days (roughly monthly or less frequent). Anything more
  frequent than that is almost always habitual spending, not a bill.

Simplification note: the research described this as an amount+interval
CLUSTERING problem (e.g. DBSCAN across all transactions). Since we already
have clean, normalized merchant names (from the categorization step earlier
in this project), grouping by merchant name first and checking amount/interval
consistency WITHIN each group achieves the same practical result without
needing a full clustering library for what is, for one person, a small
number of transactions per merchant. A true DBSCAN approach would matter
more at a scale where merchant names weren't already reliably normalized.
"""

import statistics
import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.analytics.trends import _parse_transaction_date

# Thresholds -- tunable, but reasonable defaults:
AMOUNT_CV_THRESHOLD = 0.15     # coefficient of variation in amount must be below this
INTERVAL_CV_THRESHOLD = 0.30   # coefficient of variation in interval must be below this
MIN_OCCURRENCES = 3            # need at least this many hits to call it a pattern
MIN_AVG_INTERVAL_DAYS = 20     # anything more frequent than this is "habitual", not "recurring"


def _coefficient_of_variation(values: list[float]) -> float:
    """Standard deviation / mean. Lower = more consistent. Returns 0 if mean is 0."""
    if not values or statistics.mean(values) == 0:
        return 0.0
    if len(values) < 2:
        return 0.0
    return statistics.pstdev(values) / statistics.mean(values)


def detect_recurring_payments(session: Session, user_id: uuid.UUID) -> list[dict]:
    """
    Returns a list of detected recurring payments, e.g.:
        [
            {
                "merchant": "Ajinkya",
                "category": "Rent & Housing",
                "average_amount": 5820.0,
                "average_interval_days": 30.4,
                "occurrences": 6,
                "amount_consistency": "high",
                "interval_consistency": "high",
            },
            ...
        ]
    Merchants that are frequent but irregular (e.g. food delivery) are
    correctly excluded -- see module docstring for why.
    """
    transactions = session.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.debit > 0,
        )
    ).scalars().all()

    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        by_merchant[txn.clean_merchant].append(txn)

    recurring: list[dict] = []

    for merchant, txns in by_merchant.items():
        if len(txns) < MIN_OCCURRENCES:
            continue

        sorted_txns = sorted(txns, key=lambda t: _parse_transaction_date(t.transaction_date))
        dates = [_parse_transaction_date(t.transaction_date) for t in sorted_txns]
        amounts = [float(t.debit) for t in sorted_txns]

        intervals_days = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        if not intervals_days or min(intervals_days) == 0:
            continue  # same-day duplicates or bad data, skip

        amount_cv = _coefficient_of_variation(amounts)
        interval_cv = _coefficient_of_variation(intervals_days)
        avg_interval = statistics.mean(intervals_days)

        is_recurring = (
            amount_cv <= AMOUNT_CV_THRESHOLD
            and interval_cv <= INTERVAL_CV_THRESHOLD
            and avg_interval >= MIN_AVG_INTERVAL_DAYS
        )

        if is_recurring:
            recurring.append({
                "merchant": merchant,
                "category": sorted_txns[-1].category,
                "average_amount": round(statistics.mean(amounts), 2),
                "average_interval_days": round(avg_interval, 1),
                "occurrences": len(txns),
                "amount_consistency": "high" if amount_cv <= AMOUNT_CV_THRESHOLD else "low",
                "interval_consistency": "high" if interval_cv <= INTERVAL_CV_THRESHOLD else "low",
            })

    return sorted(recurring, key=lambda r: -r["average_amount"])
