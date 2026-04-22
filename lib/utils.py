# Utility functions for Nova-Exchange
from typing import Any
import os


def join_classes(*args: Any) -> str:
    return " ".join(str(arg) for arg in args if arg)


def format_price(price: float) -> str:
    return f"{price:.2f} EUR"


def format_date(date_str: str) -> str:
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y")
    except (ValueError, AttributeError):
        return date_str


def format_relative_time(date_str: str) -> str:
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        
        if diff.days > 365:
            return f"{diff.days // 365}y ago"
        elif diff.days > 30:
            return f"{diff.days // 30}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "just now"
    except (ValueError, AttributeError):
        return date_str


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)