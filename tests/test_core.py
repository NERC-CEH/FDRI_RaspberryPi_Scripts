from unittest.mock import MagicMock

from raspberrycam.camera import DebugCamera
from raspberrycam.core import Raspberrycam
from raspberrycam.location import Location
from raspberrycam.scheduler import FdriScheduler


class MockImageManager(MagicMock):
    pass


def test_raspberrycam() -> None:
    """Will it run? -style test for the core interface"""
    location = Location(55.8626453, -3.2031049)
    sched = FdriScheduler(location)
    cam = Raspberrycam(sched, DebugCamera(256, 256), MockImageManager())

    assert isinstance(cam, Raspberrycam)
