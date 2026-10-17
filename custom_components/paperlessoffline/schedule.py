"""Sleep-time computation for quiet hours (pure logic)."""

from __future__ import annotations

from datetime import datetime, time, timedelta

QUIET_END_MARGIN = 60


def parse_time(value: str) -> time:
    """Parse ``HH:MM[:SS]``."""
    return time.fromisoformat(value)


def in_window(now: time, start: time, end: time) -> bool:
    """Whether ``now`` is inside [start, end), which may span midnight."""
    if start == end:
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end


def seconds_until(now: datetime, target: time) -> int:
    """Seconds from aware ``now`` until the next local occurrence of ``target``.

    Computed via UTC so DST transitions are accounted for.
    """
    tz = now.tzinfo
    candidate = datetime.combine(now.date(), target, tzinfo=tz)
    if candidate <= now:
        candidate = datetime.combine(now.date() + timedelta(days=1), target, tzinfo=tz)
    return int(candidate.timestamp() - now.timestamp())


def quiet_sleep(now: datetime, start: time, end: time) -> int | None:
    """Return the sleep (s) needed to skip quiet hours, or None outside them."""
    if not in_window(now.timetz().replace(tzinfo=None), start, end):
        return None
    return seconds_until(now, end) + QUIET_END_MARGIN


def quiet_change(now: datetime, start: time, end: time) -> tuple[bool, datetime]:
    """Whether aware ``now`` is in quiet hours, and when that next changes."""
    inside = in_window(now.timetz().replace(tzinfo=None), start, end)
    seconds = seconds_until(now, end if inside else start)
    return inside, datetime.fromtimestamp(now.timestamp() + seconds, now.tzinfo)
