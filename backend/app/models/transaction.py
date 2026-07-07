"""
Transaction model -- the permanent, database-backed version of what
run_categorization.py currently prints and throws away each run.

user_id is included now (even without real auth yet) so this schema doesn't
need a breaking migration later when we add login. For now every row uses
a placeholder user_id (see app/models/constants.py).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Raw parsed data
    transaction_date = Column(String, nullable=False)  # kept as string (source format varies DD-MM-YY vs DD/MM/YYYY); normalized at query time
    raw_description = Column(String, nullable=False)
    clean_merchant = Column(String, nullable=False)

    credit = Column(Numeric(12, 2), nullable=False, default=0)
    debit = Column(Numeric(12, 2), nullable=False, default=0)
    balance = Column(Numeric(12, 2), nullable=False)

    # Categorization result
    category = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    needs_review = Column(Boolean, nullable=False, default=False)

    # Provenance -- which statement/parser this came from, useful once
    # multiple statements from different months/banks get uploaded
    source_filename = Column(String, nullable=True)
    statement_format = Column(String, nullable=True)  # "relationship_summary" | "statement_of_account"

    created_at = Column(DateTime, default=datetime.utcnow)
