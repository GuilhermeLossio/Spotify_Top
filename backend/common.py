from __future__ import annotations

from typing import Any

REQUIRED_COLUMNS = ("position", "track", "artist", "streams")
DEFAULT_LIMIT = 50


class DataSourceError(RuntimeError):
    """Raised when chart data cannot be loaded or validated."""


def ensure_positive_int(value: Any, *, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise DataSourceError(f"{field_name} must be an integer.") from exc

    if parsed <= 0:
        raise DataSourceError(f"{field_name} must be greater than zero.")
    return parsed
