"""
Anomaly exclusion model -- lets the user say "never flag this merchant as
an anomaly, regardless of amount." Same personalization principle as the
categorization corrections: the user's own knowledge (e.g. "Mauli is my
regular food vendor, small or large amounts are all normal for them")
overrides a generic statistical guess.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class AnomalyExclusion(Base):
    __tablename__ = "anomaly_exclusions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    merchant_name = Column(String, nullable=False)  # stored lowercase, substring-matched
    created_at = Column(DateTime, default=datetime.utcnow)
