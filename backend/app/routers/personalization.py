"""
POST /corrections -- categorize a merchant (existing or brand-new custom
category), retroactively updating every past transaction from that
merchant, not just future ones.

POST /anomaly-exclusions -- never flag this merchant as anomalous again.

GET /categories -- every category available to this user, built-in plus
any custom ones they've created, for populating a dropdown.
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.auth import get_current_user_id
from app.categorization.rules import Category
from app.categorization.db_corrections import add_correction
from app.analytics.anomaly_exclusions import add_exclusion
from app.models.transaction import Transaction
from app.models.correction import Correction

router = APIRouter()


class SetCategoryRequest(BaseModel):
    merchant_name: str
    category: str  # existing built-in OR a brand-new custom category name


class ExcludeAnomalyRequest(BaseModel):
    merchant_name: str


@router.get("/categories")
def get_categories(user_id: uuid.UUID = Depends(get_current_user_id)):
    session: Session = SessionLocal()
    try:
        built_in = [c.value for c in Category]

        custom_from_transactions = session.execute(
            select(Transaction.category).where(Transaction.user_id == user_id).distinct()
        ).scalars().all()
        custom_from_corrections = session.execute(
            select(Correction.category).where(Correction.user_id == user_id).distinct()
        ).scalars().all()

        all_categories = set(built_in) | set(custom_from_transactions) | set(custom_from_corrections)
        # Built-ins first (stable, familiar order), then any custom ones alphabetically
        custom_only = sorted(all_categories - set(built_in))
        return {"categories": built_in + custom_only}
    finally:
        session.close()


@router.post("/corrections")
def set_category(
    body: SetCategoryRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Saves the correction AND retroactively updates every existing
    transaction from this merchant to the new category -- so it takes
    effect immediately in the dashboard, not just on the next upload.
    """
    session: Session = SessionLocal()
    try:
        add_correction(session, user_id, body.merchant_name, body.category)

        merchant_lower = body.merchant_name.strip().lower()
        all_txns = session.execute(
            select(Transaction).where(Transaction.user_id == user_id)
        ).scalars().all()

        updated_count = 0
        for txn in all_txns:
            txn_merchant_lower = txn.clean_merchant.lower()
            if merchant_lower in txn_merchant_lower or txn_merchant_lower in merchant_lower:
                txn.category = body.category
                txn.confidence = 1.0
                txn.needs_review = False
                updated_count += 1
        session.commit()

        return {"status": "saved", "category": body.category, "transactions_updated": updated_count}
    finally:
        session.close()


@router.post("/anomaly-exclusions")
def exclude_merchant(
    body: ExcludeAnomalyRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    session: Session = SessionLocal()
    try:
        add_exclusion(session, user_id, body.merchant_name)
        return {"status": "excluded", "merchant_name": body.merchant_name}
    finally:
        session.close()
