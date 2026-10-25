"""Build SoQL ``$where`` clauses for a permit type and a date window."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    """Inclusive calendar-day window, e.g. the 7 days ending yesterday."""

    start: dt.date
    end: dt.date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(f"window start {self.start} is after end {self.end}")

    @classmethod
    def last_days(cls, days: int, end: dt.date | None = None) -> Window:
        if days < 1:
            raise ValueError("days must be >= 1")
        end = end or dt.date.today() - dt.timedelta(days=1)
        return cls(end - dt.timedelta(days=days - 1), end)


def quote(value: str) -> str:
    """Quote a SoQL string literal (single quotes are doubled)."""
    return "'" + value.replace("'", "''") + "'"


def build_where(
    *,
    date_field: str,
    window: Window,
    type_field: str | None = None,
    type_value: str | None = None,
    extra: list[str] | None = None,
) -> str:
    """Return a flat ``a AND b AND c`` clause.

    Clauses are kept flat (no parentheses) on purpose: some city portals sit
    behind a WAF that rejects parenthesised ``(...) AND`` filters. To match
    several permit types, run one query per type and merge the results.
    """
    parts: list[str] = []
    if type_field and type_value:
        parts.append(f"{type_field}={quote(type_value)}")
    parts.extend(e.strip() for e in (extra or []) if e.strip())
    parts.append(f"{date_field} >= '{window.start.isoformat()}T00:00:00'")
    parts.append(f"{date_field} <= '{window.end.isoformat()}T23:59:59'")
    return " AND ".join(parts)
