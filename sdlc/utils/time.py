from datetime import UTC, datetime, timedelta


def now_utc() -> datetime:
    return datetime.now(UTC)


def parse_timespec(s: str) -> datetime:
    if s.endswith("d"):
        days = int(s[:-1])
        return now_utc() - timedelta(days=days)
    return datetime.fromisoformat(s)


def format_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def human_delta(dt: datetime) -> str:
    delta = now_utc() - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"
