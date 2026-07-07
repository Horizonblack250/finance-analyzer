"""
One-time migration: moves your existing corrections from the local
user_corrections.json file into the database, so you don't lose the
Drop/Chitale/Ajinkya/Mauli/etc. corrections you already made.

Safe to run more than once -- it updates existing DB corrections rather
than duplicating them.

Usage: python migrate_corrections_to_db.py
"""

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.categorization.corrections import load_overrides
from app.categorization.db_corrections import add_correction as add_db_correction

if __name__ == "__main__":
    json_overrides = load_overrides()

    if not json_overrides:
        print("No corrections found in user_corrections.json -- nothing to migrate.")
    else:
        session = SessionLocal()
        try:
            for merchant_name, category_value in json_overrides.items():
                add_db_correction(session, DEFAULT_USER_ID, merchant_name, category_value)
                print(f"Migrated: {merchant_name} -> {category_value}")
        finally:
            session.close()

        print(f"\nDone. Migrated {len(json_overrides)} corrections to the database.")
