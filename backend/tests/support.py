from datetime import date, timedelta


def next_monday(weeks=0):
    """A future Monday, always at least a week away."""
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    return today + timedelta(days=days_until_monday + weeks * 7)


def next_saturday(weeks=0):
    today = date.today()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        days_until_saturday = 7
    return today + timedelta(days=days_until_saturday + weeks * 7)


def future_year_start():
    """December 28 of a future year, useful for cross-year checks."""
    return date(date.today().year + 1, 12, 28)


def create_request(
    client,
    headers,
    leave_type_id,
    start,
    end,
    reason="Family event and travel arrangements.",
):
    return client.post(
        "/api/leave-requests",
        headers=headers,
        json={
            "leave_type_id": leave_type_id,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "reason": reason,
        },
    )
