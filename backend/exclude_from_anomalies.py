"""
Tell the app to never flag a specific merchant as an anomaly, regardless
of amount -- e.g. a local vendor whose prices vary a lot but are all
normal for them.

Usage: python exclude_from_anomalies.py "Mauli"
"""

import sys

from app.db import SessionLocal
from app.models.constants import DEFAULT_USER_ID
from app.analytics.anomaly_exclusions import add_exclusion

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python exclude_from_anomalies.py "MerchantName"')
        sys.exit(1)

    merchant_name = sys.argv[1]

    session = SessionLocal()
    try:
        add_exclusion(session, DEFAULT_USER_ID, merchant_name)
        print(f"Done. '{merchant_name}' will no longer be flagged as an anomaly.")
    finally:
        session.close()
