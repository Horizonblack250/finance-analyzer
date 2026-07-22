import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.analytics.trends import get_monthly_category_trends


def _linear_forecast(values: list[float]) -> float:
    n = len(values)
    x_vals = list(range(n))
    x_mean = sum(x_vals) / n
    y_mean = sum(values) / n

    numerator = sum((x_vals[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return y_mean

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    next_x = n
    prediction = slope * next_x + intercept
    return max(0.0, prediction)


def forecast_next_month(session: Session, user_id: uuid.UUID) -> dict:
    trends = get_monthly_category_trends(session, user_id)

    current_month_key = datetime.utcnow().strftime("%Y-%m")
    complete_months = sorted(m for m in trends.keys() if m != current_month_key)

    all_categories = set()
    for month_data in trends.values():
        all_categories.update(month_data.keys())

    forecasts = {}
    for category in all_categories:
        values = [trends[m].get(category, 0.0) for m in complete_months]
        first_nonzero = next((i for i, v in enumerate(values) if v > 0), None)
        if first_nonzero is None:
            continue
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
