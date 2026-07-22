import statistics
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.analytics.trends import _parse_transaction_date

AMOUNT_CV_THRESHOLD = 0.15
INTERVAL_CV_THRESHOLD = 0.30
MIN_OCCURRENCES = 3
MIN_AVG_INTERVAL_DAYS = 20


def _coefficient_of_variation(values: list[float]) -> float:
    if not values or statistics.mean(values) == 0:
        return 0.0
    if len(values) < 2:
        return 0.0
    return statistics.pstdev(values) / statistics.mean(values)


def detect_recurring_payments(session: Session, user_id: uuid.UUID) -> list[dict]:
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
            continue

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
