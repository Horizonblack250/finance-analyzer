"""
Correction model -- the permanent, database-backed replacement for
user_corrections.json. Same personalization mechanism as before (merchant
name -> category override), just persisted properly instead of living in
a local file that only exists on one machine.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Matching is substring-based at query time, same logic as the old
    # corrections.py -- stored lowercase for consistent comparison.
    merchant_name = Column(String, nullable=False)
    category = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
