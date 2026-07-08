"""
Displays a next-month spending forecast per category, based on trend
(if enough history) or simple average (if not).

Usage: python show_forecast.py
"""

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.analytics.forecasting import forecast_next_month

if __name__ == "__main__":
    session = SessionLocal()
    try:
        forecasts = forecast_next_month(session, DEFAULT_USER_ID)

        print("=" * 70)
        print("NEXT MONTH SPENDING FORECAST")
        print("=" * 70)
        for category, data in sorted(forecasts.items(), key=lambda x: -x[1]["predicted"]):
            print(f"  {category:30s} Rs.{data['predicted']:>10,.2f}  "
                  f"(method: {data['method']}, based on {data['months_used']} months)")
    finally:
        session.close()
