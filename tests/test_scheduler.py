import unittest
from datetime import datetime, timedelta
from parameterized import parameterized
from rasberrycam import scheduler
from rasberrycam.scheduler import Scheduler, ScheduleState, ScheduleListRaw

class TestScheduler(unittest.TestCase):

    def test_empty_schedule(self):
        """Test behaviour with empty schedule (Assumed always on)"""

        scheduler = Scheduler([])

        self.assertListEqual(scheduler.schedule, [])
        self.assertEqual(scheduler.get_state(datetime.now()), ScheduleState.ON)
        
    def test_scheduler_initialization(self):
        """Test Scheduler initialization with valid and invalid schedules."""
        valid_schedule: ScheduleListRaw = [
            {"time": datetime.now(), "state": ScheduleState.ON},
            {"time": datetime.now() + timedelta(minutes=10), "state": ScheduleState.OFF},
        ]
        scheduler = Scheduler(valid_schedule)
        self.assertEqual(len(scheduler.schedule), 2)
        self.assertListEqual(valid_schedule, scheduler.schedule)

        invalid_schedule: ScheduleListRaw = [
            {"time": "invalid_time", "state": ScheduleState.ON}, #type: ignore
        ]
        with self.assertRaises(TypeError):
            Scheduler(invalid_schedule)
    
    def test_scheduler_initialization_with_callable(self):
        """Test Scheduler initialization with valid and invalid schedules with callables included."""
        now = datetime.now()
        
        valid_schedule: ScheduleListRaw = [
            {"time": lambda: now - timedelta(minutes=5), "state": ScheduleState.ON},
            {"time": now, "state": ScheduleState.OFF},
            {"time": lambda: now + timedelta(minutes=5), "state": ScheduleState.ON},
        ]
        scheduler = Scheduler(valid_schedule)
        self.assertEqual(len(scheduler.schedule), len(valid_schedule))
        self.assertListEqual(valid_schedule, scheduler.schedule)

        invalid_schedule: ScheduleListRaw = [
            {"time": lambda: now + timedelta(minutes=5), "state": ScheduleState.ON},
            {"time": now, "state": ScheduleState.OFF},
            {"time": lambda: now + timedelta(minutes=5), "state": ScheduleState.ON},
        ]
        with self.assertRaises(RuntimeError):
            Scheduler(invalid_schedule)

    def test_schedule_setter_sequential_validation(self):
        """Test the schedule setter for validation of sequential times."""
        valid_schedule: ScheduleListRaw = [
            {"time": datetime.now(), "state": ScheduleState.ON},
            {"time": datetime.now() + timedelta(minutes=10), "state": ScheduleState.OFF},
        ]
        scheduler = Scheduler(valid_schedule)
        self.assertEqual(len(scheduler.schedule), 2)
        self.assertListEqual(valid_schedule, scheduler.schedule)

        invalid_schedule: ScheduleListRaw = [
            {"time": datetime.now() + timedelta(minutes=10), "state": ScheduleState.ON},
            {"time": datetime.now(), "state": ScheduleState.OFF},
        ]
        with self.assertRaises(RuntimeError):
            scheduler.schedule = invalid_schedule

    @parameterized.expand([
        [
            [
                {"time": datetime.now(), "state": ScheduleState.OFF},
                {"time": datetime.now() + timedelta(minutes=10), "state": ScheduleState.ON},
            ],
            datetime.now() + timedelta(minutes=5),
            ScheduleState.OFF,
        ],
        [
            [
                {"time": datetime.now(), "state": ScheduleState.OFF},
                {"time": datetime.now() + timedelta(minutes=10), "state": ScheduleState.ON},
            ],
            datetime.now() + timedelta(minutes=15),
            ScheduleState.ON,
        ],
    ])
    def test_get_state(self, schedule, query_time, expected_state):
        """Test the get_state method for correct state retrieval."""
        scheduler = Scheduler(schedule)
        self.assertEqual(scheduler.get_state(query_time), expected_state)

if __name__ == "__main__":
    unittest.main()