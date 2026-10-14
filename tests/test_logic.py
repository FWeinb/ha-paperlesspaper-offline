"""Pure slideshow and schedule logic."""

from __future__ import annotations

from datetime import datetime, time
import random
from zoneinfo import ZoneInfo

from custom_components.paperlessoffline import slideshow
from custom_components.paperlessoffline.schedule import in_window, quiet_sleep, seconds_until

TZ = ZoneInfo("Europe/Berlin")


def test_sequential_wraps() -> None:
    assert slideshow.next_sequential(["a", "b", "c"], "c") == "a"
    assert slideshow.next_sequential(["a", "b"], None) == "a"
    assert slideshow.next_sequential(["a", "b"], "gone") == "a"
    assert slideshow.next_sequential([], "a") is None


def test_shuffle_bag_never_repeats_current() -> None:
    rng = random.Random(3)
    for _ in range(50):
        bag = slideshow.refill_bag(["a", "b", "c", "d"], "a", rng)
        assert sorted(bag) == ["a", "b", "c", "d"]
        assert bag[0] != "a"


def test_peek_prefers_queue() -> None:
    photo, _ = slideshow.peek("shuffle", ["a", "b"], "a", "b", [])
    assert photo == "b"
    photo, bag = slideshow.peek("shuffle", ["a", "b", "c"], None, None, ["x", "c"])
    assert photo == "c"
    assert bag == ["c"]


def test_window_across_midnight() -> None:
    assert in_window(time(23), time(22), time(7))
    assert in_window(time(3), time(22), time(7))
    assert not in_window(time(12), time(22), time(7))
    assert in_window(time(13), time(12), time(14))
    assert not in_window(time(12), time(12), time(12))


def test_quiet_sleep() -> None:
    now = datetime(2026, 6, 1, 23, 0, tzinfo=TZ)
    assert quiet_sleep(now, time(22), time(7)) == 8 * 3600 + 60
    assert quiet_sleep(datetime(2026, 6, 1, 12, 0, tzinfo=TZ), time(22), time(7)) is None


def test_seconds_until_across_dst() -> None:
    # Night of the spring-forward change in Europe: 2026-03-29 02:00 -> 03:00.
    now = datetime(2026, 3, 28, 23, 0, tzinfo=TZ)
    assert seconds_until(now, time(7)) == 7 * 3600
    # Autumn: 2026-10-25 03:00 -> 02:00, the night is an hour longer.
    now = datetime(2026, 10, 24, 23, 0, tzinfo=TZ)
    assert seconds_until(now, time(7)) == 9 * 3600
