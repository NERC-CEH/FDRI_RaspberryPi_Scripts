import os
from pathlib import Path
from raspberrycam.camera import DebugCamera

def test_camera_debug():
    cam = DebugCamera(256,256)
    assert isinstance(cam, DebugCamera)
    