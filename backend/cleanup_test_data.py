"""
One-time cleanup: deletes all transactions, corrections, and anomaly
exclusions that were saved under the old DEFAULT_USER_ID placeholder
(everything we imported before real authentication existed -- your 4
statements + your friend's, all blended together).

Safe to run once. After this, your database starts genuinely clean, and
everything you upload from now on will be saved under your real logged-in
account instead.

Usage: python cleanup_test_data.py
"""

from sqlalchemy import delete

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.models.transaction import Transaction
from app.models.correction import Correction
from app.models.anomaly_exclusion import AnomalyExclusion

if __name__ == "__main__":
    session = SessionLocal()
    try:
        txn_result = session.execute(delete(Transaction).where(Transaction.user_id == DEFAULT_USER_ID))
        corr_result = session.execute(delete(Correction).where(Correction.user_id == DEFAULT_USER_ID))
        excl_result = session.execute(delete(AnomalyExclusion).where(AnomalyExclusion.user_id == DEFAULT_USER_ID))
        session.commit()

        print(f"Deleted {txn_result.rowcount} transactions")
        print(f"Deleted {corr_result.rowcount} corrections")
        print(f"Deleted {excl_result.rowcount} anomaly exclusions")
        print()
        print("Cleanup complete. Your database is now empty and ready for real use.")
    finally:
        session.close()
