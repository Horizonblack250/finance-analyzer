"""
Stores the user's self-reported monthly income/budget target -- the one
piece of data we need to answer "will I fall short next month" (we only
ever had spending data before, never a target to compare it against).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class UserBudget(Base):
    __tablename__ = "user_budgets"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    monthly_income = Column(Numeric(12, 2), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
