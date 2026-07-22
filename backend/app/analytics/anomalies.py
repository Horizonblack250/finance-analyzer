import uuid
import math
import statistics
from collections import defaultdict

from sklearn.ensemble import IsolationForest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.analytics.trends import _parse_transaction_date
from app.analytics.recurring import detect_recurring_payments
from app.analytics.anomaly_exclusions import get_excluded_merchants, is_excluded

MIN_TRANSACTIONS_FOR_DETECTION = 15


def _build_features(transactions: list[Transaction]) -> list[list[float]]:
    by_merchant: dict[str, list[float]] = defaultdict(list)
    for t in transactions:
        by_merchant[t.clean_merchant].append(float(t.debit))

    merchant_stats = {}
    for merchant, amounts in by_merchant.items():
        mean = statistics.mean(amounts)
        stdev = statistics.pstdev(amounts) if len(amounts) > 1 else 0.0
        merchant_stats[merchant] = (mean, stdev, len(amounts))

    all_amounts = [float(t.debit) for t in transactions]
    global_mean = statistics.mean(all_amounts)
    global_stdev = statistics.pstdev(all_amounts) if len(all_amounts) > 1 else 0.0

    MIN_OCCURRENCES_FOR_MERCHANT_BASELINE = 3

    features = []
    for t in transactions:
        mean, stdev, freq = merchant_stats[t.clean_merchant]
        amount = float(t.debit)

        if freq >= MIN_OCCURRENCES_FOR_MERCHANT_BASELINE:
            amount_deviation = (amount - mean) / stdev if stdev > 0 else 0.0
        elif global_stdev > 0:
            amount_deviation = (amount - global_mean) / global_stdev
        else:
            amount_deviation = 0.0
        amount_deviation = max(-5.0, min(5.0, amount_deviation))

        date = _parse_transaction_date(t.transaction_date)
        day_of_month_frac = date.day / 31.0

        log_frequency = math.log(freq + 1)

        features.append([amount_deviation, day_of_month_frac, log_frequency])

    return features


def detect_anomalies(session: Session, user_id: uuid.UUID, std_threshold: float = 2.5) -> list[dict]:
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

    transactions = [
        t for t in transactions
        if t.clean_merchant not in recurring_merchants
        and not is_excluded(t.clean_merchant, excluded_merchants)
    ]

    if len(transactions) < MIN_TRANSACTIONS_FOR_DETECTION:
        return []

    features = _build_features(transactions)

    model = IsolationForest(random_state=42)
    model.fit(features)
    scores = model.decision_function(features)

    score_mean = statistics.mean(scores)
    score_stdev = statistics.pstdev(scores)
    cutoff = score_mean - (std_threshold * score_stdev)

    anomalies = []
    for txn, score in zip(transactions, scores):
        if score < cutoff:
            anomalies.append({
                "date": txn.transaction_date,
                "merchant": txn.clean_merchant,
                "category": txn.category,
                "amount": float(txn.debit),
                "anomaly_score": round(float(score), 3),
                "source_filename": txn.source_filename,
            })

    return sorted(anomalies, key=lambda a: a["anomaly_score"])
