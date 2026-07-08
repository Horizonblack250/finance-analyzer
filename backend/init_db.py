"""
Creates all tables in the database, based on the SQLAlchemy models.
Safe to run multiple times -- it only creates tables that don't already
exist, never drops or alters existing ones.

Usage: python init_db.py
"""

from app.db import Base, engine
# Importing the model modules registers them with Base.metadata --
# without these imports, create_all() would create zero tables.
from app.models import transaction, correction, anomaly_exclusion  # noqa: F401

if __name__ == "__main__":
    print("Creating tables (if they don't already exist)...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created: transactions, corrections")
