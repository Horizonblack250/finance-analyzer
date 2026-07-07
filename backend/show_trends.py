"""
Displays monthly spending trends and month-over-month category changes,
using whatever transactions are currently in the database for the user.

Usage: python show_trends.py
"""

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.analytics.trends import get_monthly_category_trends, get_month_over_month_change

if __name__ == "__main__":
    session = SessionLocal()
    try:
        trends = get_monthly_category_trends(session, DEFAULT_USER_ID)

        print("=" * 70)
        print("MONTHLY SPENDING BY CATEGORY")
        print("=" * 70)
        for month, categories in trends.items():
            print(f"\n{month}")
            for category, total in sorted(categories.items(), key=lambda x: -x[1]):
                print(f"  {category:30s} Rs.{total:>10,.2f}")

        print()
        print("=" * 70)
        print("MONTH-OVER-MONTH CHANGE (latest month vs. prior average)")
        print("=" * 70)
        changes = get_month_over_month_change(session, DEFAULT_USER_ID)
        for category, data in sorted(changes.items(), key=lambda x: -abs(x[1]["pct_change"])):
            direction = "UP" if data["pct_change"] > 0 else "DOWN"
            print(f"  {category:30s} latest=Rs.{data['latest']:>9,.2f}  "
                  f"prior_avg=Rs.{data['prior_average']:>9,.2f}  "
                  f"{direction} {abs(data['pct_change']):.1f}%")
    finally:
        session.close()
