"""Versioned NYSE cash-equity calendar snapshot; not a live exchange-status feed.

Source dates and scope are in edge_session_calendar.json. Unknown years fail
closed. Unscheduled future closures require an explicit reviewed snapshot update.
"""
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

_RAW = Path(__file__).with_suffix(".json").read_bytes()
CALENDAR_SHA256 = hashlib.sha256(_RAW).hexdigest()
CALENDAR = json.loads(_RAW)
EASTERN = ZoneInfo("America/New_York")
PUBLICATION_BUFFER = timedelta(minutes=15)  # Research policy, not vendor guarantee.


def is_session(day):
    if isinstance(day, str):
        day = date.fromisoformat(day)
    if str(day.year) not in CALENDAR["years"]:
        raise ValueError("CALENDAR_COVERAGE_UNAVAILABLE")
    return day.weekday() < 5 and day.isoformat() not in CALENDAR["closed"]


def session_bounds(day):
    if isinstance(day, str):
        day = date.fromisoformat(day)
    if not is_session(day):
        raise ValueError("NON_SESSION_DATE: " + day.isoformat())
    close = time(13) if day.isoformat() in CALENDAR["early_close"] else time(16)
    return tuple(datetime.combine(day, t, tzinfo=EASTERN).astimezone(timezone.utc)
                 for t in (time(9, 30), close))


def eligible_cutoff(now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware research timestamp required")
    day = now.astimezone(EASTERN).date()
    while True:
        if is_session(day) and now >= session_bounds(day)[1] + PUBLICATION_BUFFER:
            return day
        day -= timedelta(days=1)


def next_session(day):
    day = date.fromisoformat(day) if isinstance(day, str) else day
    day += timedelta(days=1)
    while not is_session(day):
        day += timedelta(days=1)
    return day.isoformat()


def expected_entry_exit(signal_day, registered_at):
    day = next_session(signal_day)
    while session_bounds(day)[0] <= registered_at:
        day = next_session(day)
    return day, next_session(day)


def validate_sequence(days, *, now=None, require_fresh=False):
    if not days or days != sorted(set(days)):
        raise ValueError("INVALID_SESSION_SEQUENCE")
    for day in days:
        session_bounds(day)
    for before, after in zip(days, days[1:]):
        if next_session(before) != after:
            raise ValueError("MISSING_MARKET_SESSION: " + next_session(before))
    if require_fresh and days[-1] != eligible_cutoff(now).isoformat():
        raise ValueError("STALE_OR_FUTURE_SOURCE_SESSION")
