"""
Displays detected anomalous transactions -- unusual amounts relative to
each merchant's own normal pattern (not just large transactions overall).

Usage: python show_anomalies.py
"""

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.analytics.anomalies import detect_anomalies

if __name__ == "__main__":
    session = SessionLocal()
    try:
        anomalies = detect_anomalies(session, DEFAULT_USER_ID)

        print("=" * 70)
        print(f"DETECTED ANOMALIES ({len(anomalies)} found)")
        print("=" * 70)
        if not anomalies:
            print("No anomalies detected (or not enough transaction history yet).")
        for a in anomalies:
            print(f"\n{a['date']} | {a['merchant']} ({a['category']})")
            print(f"  Amount: Rs.{a['amount']:,.2f}")
            print(f"  Anomaly score: {a['anomaly_score']} (more negative = more unusual)")
    finally:
        session.close()
