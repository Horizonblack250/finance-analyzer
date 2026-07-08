"""
Spending forecasting: predicts next month's likely spend per category.

Design choice: with only a handful of months of history per category (not
years), a heavy time-series model (Prophet, ARIMA) would be overfitting risk
for very little benefit -- these models need substantially more data points
to outperform something simple. Instead:

- >=3 complete months of history for a category -> linear regression
  (least-squares trend line) extrapolated one step ahead. This captures
  "trending up" or "trending down" without overfitting.
- 1-2 months of history -> plain average (not enough points to fit a
  trend line meaningfully; a trend from 2 points is just noise).
- 0 months -> no forecast possible.

The current in-progress month is excluded from the input data, same
reasoning as trends.py: a partial month isn't a real data point.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.trends import get_monthly_category_trends
from datetime import datetime


def _linear_forecast(values: list[float]) -> float:
    """
    Fits a straight line (least squares) through the values (x = 0,1,2,...)
    and returns the predicted next value. Pure Python, no numpy needed for
    something this small.
    """
    n = len(values)
    x_vals = list(range(n))
    x_mean = sum(x_vals) / n
    y_mean = sum(values) / n

    numerator = sum((x_vals[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return y_mean  # all x the same (shouldn't happen here), fall back to average

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    next_x = n  # predicting one step past the last known point
    prediction = slope * next_x + intercept
    return max(0.0, prediction)  # spending can't be negative


def forecast_next_month(session: Session, user_id: uuid.UUID) -> dict:
    """
    Returns a forecast per category, e.g.:
        {
            "Food Delivery": {"predicted": 8500.0, "method": "trend", "months_used": 5},
            "Rent & Housing": {"predicted": 5820.0, "method": "average", "months_used": 2},
        }
    """
    trends = get_monthly_category_trends(session, user_id)

    current_month_key = datetime.utcnow().strftime("%Y-%m")
    complete_months = sorted(m for m in trends.keys() if m != current_month_key)

    all_categories = set()
    for month_data in trends.values():
        all_categories.update(month_data.keys())

    forecasts = {}
    for category in all_categories:
        values = [trends[m].get(category, 0.0) for m in complete_months]
        # Trim leading zeros -- if a category only started appearing recently,
        # don't let months before it existed drag the trend/average down.
        first_nonzero = next((i for i, v in enumerate(values) if v > 0), None)
        if first_nonzero is None:
            continue  # category never had any spend in complete months
        values = values[first_nonzero:]

        if len(values) >= 3:
            predicted = _linear_forecast(values)
            method = "trend"
        else:
            predicted = sum(values) / len(values)
            method = "average"

        forecasts[category] = {
            "predicted": round(predicted, 2),
            "method": method,
            "months_used": len(values),
        }

    return forecasts
