"""
Creates all tables in the database, based on the SQLAlchemy models.
Safe to run multiple times.

Usage: python init_db.py
"""

from app.db import Base, engine
from app.models import transaction, correction, anomaly_exclusion, user_budget, uploaded_file, chat_conversation, chat_message  # noqa: F401 # noqa: F401

if __name__ == "__main__":
    print("Creating tables (if they don't already exist)...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables: transactions, corrections, anomaly_exclusions, user_budgets, uploaded_files")
