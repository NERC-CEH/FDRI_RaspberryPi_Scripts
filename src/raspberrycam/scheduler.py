import logging
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Callable, List, TypedDict

from raspberrycam.location import Location

logger = logging.getLogger(__name__)


class ScheduleState(Enum):
    """Valid schedule states"""

    OFF = 0
    ON = 1


class ScheduleItemRaw(TypedDict):
    """Type for schedule item as it is stored. "time" may be a datetime or a
    callable that returns a datetime"""

    time: Callable[[], datetime] | datetime
    state: ScheduleState


class ScheduleItem(TypedDict):
    """Type for a schedule item. "time" can only be a datetime"""

    time: datetime
    state: ScheduleState


ScheduleListRaw = List[ScheduleItemRaw]
"""Helper type for a list of raw schedule items"""

ScheduleList = List[ScheduleItem]
"""Helper type for a list of schedule items"""


class FdriScheduler:
    """Scheduling class for managing schedules in FDRI devices"""

    location: Location
    """Location of the device, used to calculate the sunrise/sunset time"""

    def __init__(self, location: Location) -> None:
        """
        Args:
            location: The temporal location of the device
        """
        self.location = location

    def get_schedule(self, time: date) -> ScheduleList:
        """Gets a schedule list for the date specified.
        Args:
            time: The time to query
        Returns:
            A list of schedules
        """
        stats = self.location.get_sun_stats(time)

        return [
            {"time": stats["sunrise"], "state": ScheduleState.ON},
            {"time": stats["sunset"], "state": ScheduleState.OFF},
        ]

    def get_next_on_time(self, time: datetime) -> datetime:
        """Gets next ON state after the provided datetime which may roll over into the
            next day
        Args:
            time: The datetime to search after
        Returns:
            A datetime object of the next ON state
        """
        for item in self.get_schedule(time.date()):
            if item["time"] > time and item["state"] == ScheduleState.ON:
                return item["time"]

        for item in self.get_schedule((time + timedelta(days=1)).date()):
            if item["time"] > time and item["state"] == ScheduleState.ON:
                return item["time"]

        raise RuntimeError("No next on time found")

    def get_state(self, time: datetime) -> ScheduleState:
        """Returns the state at a given datetime
        Args:
            time: The datetime to query
        Returns:
            A state object
        """

        state = None
        for item in self.get_schedule(time):
            if time >= item["time"]:
                state = item["state"]

        if not state:
            state = ScheduleState.ON

        return state
