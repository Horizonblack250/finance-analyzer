"""
Anomaly detection: flags individual transactions that look unusual.

Key design decision (the research was explicit about this pitfall): a naive
model using raw transaction amount would flag rent/EMI payments as
anomalies every single month, simply because they're larger than most
transactions. That's wrong -- ₹5,820 is completely normal for THIS
merchant (your landlord), even though it's unusual compared to your
average ₹100 Zomato order.

The fix: instead of raw amount, we use each transaction's deviation from
its OWN merchant's historical average (in standard-deviation units) as the
primary feature. A regular ₹5,820 rent payment has ~0 deviation from
Ajinkya's own average and won't be flagged. A one-off ₹15,000 medical bill
that doesn't match any merchant's normal pattern WILL show a large
deviation and correctly gets flagged.

We use Isolation Forest (unsupervised) since we have no labeled "this was
actually unusual" data to train against -- exactly the situation the
research flagged this technique as appropriate for.
"""

import uuid
import math
import statistics
from collections import defaultdict

from sklearn.ensemble import IsolationForest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.analytics.trends import _parse_transaction_date

MIN_TRANSACTIONS_FOR_DETECTION = 15  # need a reasonable amount of data before this is meaningful


def _build_features(transactions: list[Transaction]) -> list[list[float]]:
    """
    Builds a 3-feature vector per transaction:
      1. Amount deviation from THIS MERCHANT's own average, in std-dev units
         (capped at +/-5 to avoid one extreme outlier distorting the scale)
      2. Day of month (as a fraction 0-1) -- catches unusual TIMING, e.g. a
         big purchase on a day nothing normally happens
      3. log(merchant frequency + 1) -- how often this merchant appears at
         all; rare/one-off merchants get more scrutiny than frequent ones
    """
    by_merchant: dict[str, list[float]] = defaultdict(list)
    for t in transactions:
        by_merchant[t.clean_merchant].append(float(t.debit))

    merchant_stats = {}
    for merchant, amounts in by_merchant.items():
        mean = statistics.mean(amounts)
        stdev = statistics.pstdev(amounts) if len(amounts) > 1 else 0.0
        merchant_stats[merchant] = (mean, stdev, len(amounts))

    # Global baseline -- used as a fallback for merchants with too little
    # history of their own (a merchant seen only once or twice has no
    # meaningful "normal" to compare against; comparing it to itself always
    # yields zero deviation, which would hide a genuine one-off anomaly like
    # a single unusually large purchase from a merchant never seen again).
    all_amounts = [float(t.debit) for t in transactions]
    global_mean = statistics.mean(all_amounts)
    global_stdev = statistics.pstdev(all_amounts) if len(all_amounts) > 1 else 0.0

    MIN_OCCURRENCES_FOR_MERCHANT_BASELINE = 3

    features = []
    for t in transactions:
        mean, stdev, freq = merchant_stats[t.clean_merchant]
        amount = float(t.debit)

        if freq >= MIN_OCCURRENCES_FOR_MERCHANT_BASELINE:
            # Enough history with this merchant to judge against its OWN
            # pattern. If it's perfectly consistent (stdev == 0, e.g. rent
            # that's identical every month), that correctly means zero
            # deviation -- it should NOT fall through to the global baseline.
            amount_deviation = (amount - mean) / stdev if stdev > 0 else 0.0
        elif global_stdev > 0:
            amount_deviation = (amount - global_mean) / global_stdev
        else:
            amount_deviation = 0.0
        amount_deviation = max(-5.0, min(5.0, amount_deviation))  # cap extreme values

        date = _parse_transaction_date(t.transaction_date)
        day_of_month_frac = date.day / 31.0

        log_frequency = math.log(freq + 1)

        features.append([amount_deviation, day_of_month_frac, log_frequency])

    return features


from app.analytics.recurring import detect_recurring_payments
from app.analytics.anomaly_exclusions import get_excluded_merchants, is_excluded


def detect_anomalies(session: Session, user_id: uuid.UUID, std_threshold: float = 2.5) -> list[dict]:
    """
    Returns transactions flagged as anomalous, most unusual first.

    Design fix #1: an earlier version used IsolationForest's `contamination`
    parameter (a fixed expected percentage, e.g. 5%) to decide how many
    transactions to flag. That's a real flaw -- it forces exactly ~5% of
    ALL transactions to be labeled anomalous NO MATTER WHAT, even once
    genuinely unusual ones run out, so it starts flagging ordinary small
    transactions (a Rs.14.50 Uber ride) just to hit the quota. Fixed by
    using a statistical cutoff on the score distribution instead (see below).

    Design fix #2: testing at realistic scale revealed that the
    log(merchant frequency) feature was flagging legitimate recurring bills
    (rent, seen only ~6 times over 6 months) as anomalous, simply because
    daily habitual purchases (Zomato, Uber) occur far more often. A bill
    isn't suspicious for happening less often than a daily habit. Since
    recurring.py already has a principled answer for "is this merchant a
    known, legitimate recurring payment", we exclude those merchants here
    entirely rather than inventing a second, competing heuristic for the
    same question.

    Personalization: the user can also explicitly say "never flag this
    merchant" (e.g. a regular local vendor whose amounts vary a lot but are
    all normal) via anomaly_exclusions -- this is the same principle as the
    categorization corrections, applied here.
    """
    transactions = list(session.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.debit > 0,
        )
    ).scalars().all())

    if len(transactions) < MIN_TRANSACTIONS_FOR_DETECTION:
        return []  # not enough data for this to be meaningful yet

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
    scores = model.decision_function(features)  # lower = more anomalous

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
