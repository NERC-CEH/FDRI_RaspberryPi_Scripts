from datetime import datetime, timedelta

from dateutil.tz import tzlocal

from raspberrycam.location import Location
from raspberrycam.scheduler import FdriScheduler, ScheduleState


def test_scheduler() -> None:
    # Bus stop outside UKCEH Edinburgh
    location = Location(55.8626453, -3.2031049)

    sched = FdriScheduler(location)

    schedule = sched.get_schedule(datetime.now())
    assert len(schedule), 2
    # Sunrise
    assert schedule[0]["state"] == ScheduleState.ON
    # Sunset
    assert schedule[1]["state"] == ScheduleState.OFF

    dt = datetime(2025, 6, 6, 16, 0, tzinfo=tzlocal())
    # Note that returned time is in UTC
    on_time = sched.get_next_on_time(dt)

    # Let's just check it comes back as tomorrow
    assert on_time.date() == (dt + timedelta(days=1)).date()
