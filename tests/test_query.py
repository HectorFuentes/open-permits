import datetime as dt

import pytest

from open_permits.query import Window, build_where, quote


def test_last_days_inclusive():
    w = Window.last_days(7, dt.date(2026, 10, 23))
    assert (w.start, w.end) == (dt.date(2026, 10, 17), dt.date(2026, 10, 23))


def test_window_rejects_reversed_and_zero():
    with pytest.raises(ValueError):
        Window(dt.date(2026, 10, 2), dt.date(2026, 10, 1))
    with pytest.raises(ValueError):
        Window.last_days(0, dt.date(2026, 10, 1))


def test_quote_escapes_single_quotes():
    assert quote("O'Brien") == "'O''Brien'"


def test_build_where_is_flat():
    w = Window(dt.date(2026, 10, 19), dt.date(2026, 10, 23))
    clause = build_where(
        date_field="issue_permit_date",
        window=w,
        type_field="application_type",
        type_value="Plumbing",
        extra=["worktype='Roof'", "  "],
    )
    assert clause == (
        "application_type='Plumbing' AND worktype='Roof' AND "
        "issue_permit_date >= '2026-10-19T00:00:00' AND issue_permit_date <= '2026-10-23T23:59:59'"
    )
    assert "(" not in clause


def test_build_where_without_type():
    w = Window(dt.date(2026, 10, 1), dt.date(2026, 10, 1))
    assert build_where(date_field="d", window=w).startswith("d >= '2026-10-01")
