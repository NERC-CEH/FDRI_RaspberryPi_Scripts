import logging
import time
from datetime import datetime

from dateutil.tz import tzlocal

from raspberrycam import raspberrypi
from raspberrycam.camera import CameraInterface
from raspberrycam.image import S3ImageManager
from raspberrycam.scheduler import FdriScheduler, ScheduleState

logger = logging.getLogger(__name__)


class Rasberrycam:
    """Core class for managing a RasberryPi camera deployment"""

    scheduler: FdriScheduler
    """The scheduler used to control the RasberryPi state"""

    camera: CameraInterface
    """A physical/virtual camera to take images"""

    capture_interval: int
    """Frequency of image captures in seconds"""

    image_manager: S3ImageManager
    """Image manager used to manipulate image files"""

    _intervals_since_last_upload: int
    """Tracks how many images have been captured since the last upload,
        Allows the app to bulk upload images"""

    def __init__(
        self,
        scheduler: FdriScheduler,
        camera: CameraInterface,
        image_manager: S3ImageManager,
        capture_interval: int = 300,
        debug: bool = False,
    ) -> None:
        """
        Args:
            scheduler: The scheduler used to control the RasberryPi state
            camera: The camera interface used
            image_manager: The image management object
            debug: Flag to activate debug mode
        """
        self.scheduler = scheduler
        self.camera = camera
        self.capture_interval = capture_interval
        self.image_manager = image_manager
        self._intervals_since_last_upload = 0
        self.debug = debug

    def run(self) -> None:
        """Runs main loop of code until exited"""

        raspberrypi.set_governer(raspberrypi.GovernorMode.ONDEMAND, debug=self.debug)
        while True:
            now = datetime.now(tzlocal())
            state = self.scheduler.get_state(now)

            if state == ScheduleState.OFF:
                # Instead of exiting, wait until the next ON time
                logger.info("Camera is in OFF state (nighttime), waiting...")
                next_on_time = self.scheduler.get_next_on_time(now)
                logger.info(f"Next ON time: {next_on_time}")

                # Sleep until close to the next ON time
                sleep_duration = (next_on_time - now).total_seconds()
                if sleep_duration > 0:
                    # Sleep for most of the duration, but wake up occasionally to check
                    # In case of time changes, system restarts, etc.
                    while sleep_duration > 300:  # 5 minutes
                        time.sleep(300)
                        sleep_duration -= 300
                        # Re-check the time in case something changed
                        now = datetime.now(tzlocal())
                        if self.scheduler.get_state(now) == ScheduleState.ON:
                            break
                        next_on_time = self.scheduler.get_next_on_time(now)
                        sleep_duration = (next_on_time - now).total_seconds()

                    # Sleep the remaining time
                    if sleep_duration > 0:
                        time.sleep(sleep_duration)

                continue  # Go back to the start of the loop to check state again

            # Camera is ON - take pictures
            logger.info("Camera is in ON state, capturing image...")
            self.camera.capture_image(self.image_manager.get_pending_image_path())

            if len(self.image_manager.get_pending_images()) > 0:
                raspberrypi.set_governer(raspberrypi.GovernorMode.PERFORMANCE, debug=self.debug)
                self.image_manager.upload_pending(debug=self.debug)

            time.sleep(self.capture_interval)
