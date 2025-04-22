import logging
import subprocess
from datetime import datetime
from enum import StrEnum

logger = logging.getLogger(__name__)


class GovernorMode(StrEnum):
    """Enum for allowed governor states in a RasberryPi"""

    POWERSAVE = "powersave"
    ONDEMAND = "ondemand"
    PERFORMANCE = "performance"
    USERSPACE = "userspace"
    CONSERVATIVE = "conservative"


def set_governer(mode: GovernorMode, debug: bool = False) -> None:
    """Sets the governor mode.
    Args:
        mode: A GovernorMode enum
        debug: Flag for setting debug mode
    """

    try:
        if not isinstance(mode, GovernorMode):
            raise TypeError("mode is not a valid GovernorMode.")

        logger.info(f"Setting CPU governor to {mode.value}.")
        if debug:
            logger.info("Governor set")
            return

        subprocess.call(["sudo", "cpufreq-set", "-g", mode], shell=True)
    except Exception as e:
        logger.error(f"Failed to set CPU governor: {e}")


def shutdown(debug: bool = False) -> None:
    """Shuts down the device
    Args:
        debug: Flag for setting debug mode
    """

    try:
        logger.info("Initiating system shutdown")
        if debug:
            logger.info("Shut down")
            return

        # Final sync to make sure all data is written
        subprocess.run("sync", shell=True, check=False)

        # Execute shutdown command
        subprocess.run(["sudo", "shutdown", "-h", "now"], shell=True, check=False)
    except Exception as e:
        logger.error(f"Failed to shutdown: {e}")


def schedule_wakeup(wake_time: datetime, debug: bool = False) -> None:
    """Schedules a wakeup time for the device
    Args:
        wake_time: The time to wake up
        debug: Flag for setting debug mode
    """

    try:
        epoch_time = int(wake_time.timestamp())
        logger.info(f"Scheduling wakeup at {wake_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if debug:
            logger.debug("Wakeup time set")
        subprocess.run(["sudo", "rtcwake", "-m", "no", "-t", str(epoch_time)], shell=True, check=False)
    except Exception as e:
        logger.error(f"Failed to schedule wakeup: {e}")
