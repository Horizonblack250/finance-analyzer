"""
Manages user-specified anomaly exclusions: merchants the user has said
should never be flagged as anomalous, regardless of amount.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.anomaly_exclusion import AnomalyExclusion


def add_exclusion(session: Session, user_id: uuid.UUID, merchant_name: str) -> None:
    """Records that this merchant should never be flagged as an anomaly."""
    merchant_lower = merchant_name.strip().lower()

    existing = session.execute(
        select(AnomalyExclusion).where(
            AnomalyExclusion.user_id == user_id,
            AnomalyExclusion.merchant_name == merchant_lower,
        )
    ).scalar_one_or_none()

    if existing is None:
        session.add(AnomalyExclusion(user_id=user_id, merchant_name=merchant_lower))
        session.commit()


def get_excluded_merchants(session: Session, user_id: uuid.UUID) -> set[str]:
    """Returns the set of merchant name substrings the user has excluded."""
    exclusions = session.execute(
        select(AnomalyExclusion).where(AnomalyExclusion.user_id == user_id)
    ).scalars().all()
    return {e.merchant_name for e in exclusions}


def is_excluded(clean_merchant: str, excluded_merchants: set[str]) -> bool:
    """
    Substring match, same reasoning as categorization corrections: the
    normalized merchant name may include extra words the user didn't type
    (e.g. excluding "Mauli" should also match the stored "Mauli Fr").
    """
    merchant_lower = clean_merchant.lower()
    return any(excluded in merchant_lower or merchant_lower in excluded for excluded in excluded_merchants)
