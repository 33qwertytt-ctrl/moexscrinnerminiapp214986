"""Date helper utilities."""

from datetime import date, timedelta


def add_days(start_date: date, days: int) -> date:
    """Return date shifted by day count."""
    return start_date + timedelta(days=days)
