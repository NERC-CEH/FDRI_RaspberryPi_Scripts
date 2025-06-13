import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from raspberrycam.camera import DebugCamera, PiCamera


# A fake camera object we could use for testing PiCamera
class MockCamera(MagicMock):
    pass


def test_camera_debug(tmp_path: Path) -> None:
    # tmp_path is a "pytest fixture", temp directory that lasts for the test
    cam = DebugCamera(256, 256)
    assert isinstance(cam, DebugCamera)

    image_path = tmp_path / "test.txt"
    cam.capture_image(image_path, vflip=True, hflip=True)

    # Test the logic of the debug options
    assert os.path.exists(image_path)
    with open(image_path, "r") as img:
        output = img.read()
        assert "upside-down and mirrored" in output

    cam.capture_image(image_path, vflip=True)
    with open(image_path, "r") as img:
        output = img.read()
        assert "mirrored" not in output


@pytest.mark.raspi
def test_picamera() -> None:
    cam = PiCamera(256, 256)
    assert isinstance(cam, PiCamera)

    # replace the real pi camera interface with a mock one
    # cam._camera = MockCamera()

    cam.capture_image("test.jpg", vflip=True)
