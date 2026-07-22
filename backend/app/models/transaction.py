import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    transaction_date = Column(String, nullable=False)
    raw_description = Column(String, nullable=False)
    clean_merchant = Column(String, nullable=False)

    credit = Column(Numeric(12, 2), nullable=False, default=0)
    debit = Column(Numeric(12, 2), nullable=False, default=0)
    balance = Column(Numeric(12, 2), nullable=False)

    category = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    needs_review = Column(Boolean, nullable=False, default=False)

    source_filename = Column(String, nullable=True)
    statement_format = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
