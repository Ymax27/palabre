from datetime import UTC, datetime, timedelta


def week_start(moment: datetime | None = None) -> datetime:
    now = (moment or datetime.now(UTC)).astimezone(UTC)
    monday = now.date() - timedelta(days=now.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=UTC)


def week_end(start: datetime) -> datetime:
    return start + timedelta(days=7) - timedelta(microseconds=1)
