from enum import Enum
from typing import Callable, List, Tuple, Type, TypedDict
from datetime import datetime

class ScheduleState(Enum):
    """Valid schedule states"""
    OFF = 0
    ON = 1

class ScheduleItemRaw(TypedDict):
    time: Callable[[], datetime] | datetime
    state: ScheduleState

class ScheduleItem(TypedDict):
    time: datetime
    state: ScheduleState

type ScheduleListRaw = List[ScheduleItemRaw]
type ScheduleList = List[ScheduleItem]


class Scheduler:

    def __init__(self, schedule: List[ScheduleItemRaw]) -> None:
        self.schedule = schedule

    @property
    def schedule(self) -> List[ScheduleItem]:

        items: ScheduleList = []
        for item in self._schedule:
            time = item["time"]() if isinstance(item["time"], Callable) else item["time"]
            items.append({"time": time, "state": item["state"]})

        return items
    @schedule.setter
    def schedule(self, schedule: ScheduleListRaw) -> None:
        if not hasattr(schedule, "__iter__"):
            schedule = [schedule] #type: ignore

        # last_item = None
        for i, item in enumerate(schedule):
            # Check schedule type
            if not isinstance(item["time"], (Callable, datetime)):
                raise TypeError(f"Schedule item must be a Callable or datetime, not '{type(item["time"])}'")

            # Check current item is later than last item
            if i > 0:
                this_item = item
                last_item = schedule[i-1]
                if isinstance(this_item["time"], Callable):
                    this_item["time"] = this_item["time"]()
                if isinstance(last_item["time"], Callable):
                    last_item["time"] = last_item["time"]()
                
                if this_item["time"] <= last_item["time"]:
                    raise RuntimeError("Schedule items must be unique and sequential")
        
        self._schedule = schedule

    def get_state(self, time: datetime) -> ScheduleState:
        """Returns an enum of the desired state"""
        
        state = ScheduleState.ON
        for item in self.schedule:
            if time >= item["time"]:
                state = item["state"]
        
        return state
            