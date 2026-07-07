"""
Database-backed version of the personalization corrections mechanism.
Same idea as the old corrections.py (JSON file), but now stored per-user
in the database so it survives across machines/deployments and can
eventually be scoped to real logged-in users instead of one shared file.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.correction import Correction


def add_correction(session: Session, user_id: uuid.UUID, merchant_name: str, category: str) -> None:
    """Records a correction. If one already exists for this merchant name
    (for this user), updates it instead of creating a duplicate."""
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
    """
    Returns the corrected category for this merchant, if the user has one
    saved. Substring matching (not exact) -- same reasoning as before: the
    normalized merchant name may include extra words the user didn't type
    when correcting it (e.g. "Drop" should still match "Drop It").
    """
    merchant_lower = merchant_name.strip().lower()

    corrections = session.execute(
        select(Correction).where(Correction.user_id == user_id)
    ).scalars().all()

    for correction in corrections:
        if correction.merchant_name in merchant_lower or merchant_lower in correction.merchant_name:
            return correction.category
    return None
