"""
Displays detected recurring payments (rent, subscriptions, bills) from
the transactions currently in the database.

Usage: python show_recurring.py
"""

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.analytics.recurring import detect_recurring_payments

if __name__ == "__main__":
    session = SessionLocal()
    try:
        recurring = detect_recurring_payments(session, DEFAULT_USER_ID)

        print("=" * 70)
        print(f"DETECTED RECURRING PAYMENTS ({len(recurring)} found)")
        print("=" * 70)
        if not recurring:
            print("No recurring payments detected yet -- need more months of data.")
        for item in recurring:
            print(f"\n{item['merchant']} ({item['category']})")
            print(f"  Average amount:   Rs.{item['average_amount']:,.2f}")
            print(f"  Average interval: every {item['average_interval_days']} days")
            print(f"  Seen {item['occurrences']} times")
    finally:
        session.close()
