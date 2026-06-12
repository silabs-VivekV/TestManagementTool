"""Shared helper to classify an assignment against its ETA (target deadline)."""

from __future__ import annotations

from datetime import date, datetime

ON_TIME = "On time"
LATE = "Late"
OVERDUE = "Overdue"
ON_TRACK = "On track"
NO_ETA = "No ETA"

_COMPLETED_VALUES = {"PASSED", "FAILED"}


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def deadline_status(eta, status, completed_date, today: date | None = None) -> str:
    """Return a deadline category for one assignment.

    - Completed (Passed/Failed) with an ETA -> "On time" / "Late"
    - Not completed with an ETA -> "Overdue" (past ETA) / "On track"
    - No ETA set -> "No ETA"
    """
    eta_d = _as_date(eta)
    if eta_d is None:
        return NO_ETA

    status_val = getattr(status, "value", status)
    today = today or date.today()

    if status_val in _COMPLETED_VALUES:
        done = _as_date(completed_date)
        if done is None:
            return ON_TIME
        return ON_TIME if done <= eta_d else LATE

    return OVERDUE if today > eta_d else ON_TRACK
