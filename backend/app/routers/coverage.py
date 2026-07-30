"""
GET /coverage -- what date range the user's uploaded data currently spans.
Used on the Upload page so the user always knows what's missing, instead
of guessing whether they've already uploaded a given month.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.auth import get_current_user_id
from app.analytics.coverage import get_data_coverage

router = APIRouter()


@router.get("/coverage")
def coverage(user_id: uuid.UUID = Depends(get_current_user_id)):
    session: Session = SessionLocal()
    try:
        return get_data_coverage(session, user_id)
    finally:
        session.close()
