import logging
from PIL import Image
from dateutil.tz import tzlocal
from rasberrycam import image
from rasberrycam.camera import CameraInterface, LibCamera
from rasberrycam.image import ImageManager, S3ImageManager
from rasberrycam.s3 import S3Manager
from rasberrycam.scheduler import FdriScheduler, ScheduleState
from rasberrycam import rasberrypi
from rasberrycam.temporal import TemporalLocation, get_timezone
from platformdirs import user_data_dir
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class Rasberrycam:
    """Core class for managing application"""

    scheduler: FdriScheduler
    camera: CameraInterface
    capture_interval: int
    app_directory: str
    s3_manager: S3Manager
    image_manager: S3ImageManager

    def __init__(
        self,
        scheduler: FdriScheduler,
        camera: CameraInterface,
        image_manager: S3ImageManager,
        capture_interval: int = 300,
        debug: bool = False
    ) -> None:
        self.scheduler = scheduler
        self.camera = camera
        self.capture_interval = capture_interval
        self.image_manager = image_manager
        self._intervals_since_last_upload = 0
        self.debug = debug

    def run(self) -> None:
        """Runs main loop of code until exited"""

        rasberrypi.set_governer(rasberrypi.GovernorMode.ONDEMAND, debug=self.debug)
        while True:
            now = datetime.now(tzlocal())
            state = self.scheduler.get_state(now)

            if state == ScheduleState.OFF:
                rasberrypi.schedule_wakeup(self.scheduler.get_next_on_time(now), debug=self.debug)
                rasberrypi.shutdown(debug=self.debug)
                if self.debug:
                    break
            
            self.camera.capture_image(self.image_manager.get_pending_image_path())

            self.image_manager.upload_pending(debug=self.debug)
            
            time.sleep(self.capture_interval)