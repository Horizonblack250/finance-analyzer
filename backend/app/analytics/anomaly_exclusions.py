import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.anomaly_exclusion import AnomalyExclusion


def add_exclusion(session: Session, user_id: uuid.UUID, merchant_name: str) -> None:
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
    exclusions = session.execute(
        select(AnomalyExclusion).where(AnomalyExclusion.user_id == user_id)
    ).scalars().all()
    return {e.merchant_name for e in exclusions}


def is_excluded(clean_merchant: str, excluded_merchants: set[str]) -> bool:
    merchant_lower = clean_merchant.lower()
    return any(excluded in merchant_lower or merchant_lower in excluded for excluded in excluded_merchants)
