import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.correction import Correction


def add_correction(session: Session, user_id: uuid.UUID, merchant_name: str, category: str) -> None:
    merchant_lower = merchant_name.strip().lower()

    existing = session.execute(
        select(Correction).where(
            Correction.user_id == user_id,
            Correction.merchant_name == merchant_lower,
        )
    ).scalar_one_or_none()

    if existing:
        existing.category = category
    else:
        session.add(Correction(
            user_id=user_id,
            merchant_name=merchant_lower,
            category=category,
        ))
    session.commit()


def get_override(session: Session, user_id: uuid.UUID, merchant_name: str) -> str | None:
    merchant_lower = merchant_name.strip().lower()

    corrections = session.execute(
        select(Correction).where(Correction.user_id == user_id)
    ).scalars().all()

    for correction in corrections:
        if correction.merchant_name in merchant_lower or merchant_lower in correction.merchant_name:
            return correction.category
    return None
