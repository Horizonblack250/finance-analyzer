"""
Diagnostic script: shows the raw per-transaction data behind recurring
detection for a specific merchant, so we can see exactly why it is or
isn't being flagged as recurring.

Usage: python debug_recurring.py "Ajinkya"
"""

import sys
import statistics

from sqlalchemy import select

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.models.transaction import Transaction
from app.analytics.trends import _parse_transaction_date

if __name__ == "__main__":
    merchant_search = sys.argv[1] if len(sys.argv) > 1 else "Ajinkya"

    session = SessionLocal()
    try:
        all_txns = session.execute(
            select(Transaction).where(
                Transaction.user_id == DEFAULT_USER_ID,
                Transaction.debit > 0,
            )
        ).scalars().all()

        matches = [t for t in all_txns if merchant_search.lower() in t.clean_merchant.lower()]

        print(f"Found {len(matches)} transactions where clean_merchant contains '{merchant_search}'")
        print()

        # Show EXACTLY what clean_merchant string each one has -- to catch
        # any inconsistent naming (extra spaces, different capitalization, etc.)
        merchant_names_seen = set(t.clean_merchant for t in matches)
        print(f"Distinct clean_merchant values seen: {merchant_names_seen}")
        print()

        sorted_matches = sorted(matches, key=lambda t: _parse_transaction_date(t.transaction_date))
        print(f"{'Date':12s} {'Clean Merchant':20s} {'Debit':>10s} {'Source File'}")
        for t in sorted_matches:
            source = (t.source_filename or "").split("\\")[-1].split("/")[-1]
            print(f"{t.transaction_date:12s} {t.clean_merchant:20s} {float(t.debit):>10,.2f} {source}")

        if len(sorted_matches) >= 2:
            dates = [_parse_transaction_date(t.transaction_date) for t in sorted_matches]
            amounts = [float(t.debit) for t in sorted_matches]
            intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            print()
            print(f"Amounts: {amounts}")
            print(f"Intervals (days): {intervals}")
            if intervals:
                print(f"Min interval: {min(intervals)} days")
                if 0 in intervals:
                    print("*** WARNING: a 0-day interval exists -- this would cause the whole merchant to be SKIPPED by detect_recurring_payments ***")
    finally:
        session.close()
