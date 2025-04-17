from datetime import datetime
from enum import StrEnum
import logging
import subprocess

logger = logging.getLogger(__name__)


class GovernorMode(StrEnum):
    POWERSAVE = "powersave"
    ONDEMAND = "ondemand"
    PERFORMANCE = "performance"
    USERSPACE = "userspace"
    CONSERVATIVE = "conservative"


def set_governer(mode: GovernorMode, debug=False) -> None:
    try:
        if not isinstance(mode, GovernorMode):
            raise TypeError(f"mode is not a valid GovernorMode.")

        logger.info(f"Setting CPU governor to {mode.value}.")
        if debug:
            logger.info("Governor set")
            return

        subprocess.call(["sudo", "cpufreq-set", "-g", mode], shell=True)
    except Exception as e:
        logger.error(f"Failed to set CPU governor: {e}")


def shutdown(debug=False) -> None:
    try:
        logger.info("Initiating system shutdown")
        if debug:
            logger.info("Shut down")
            return

        # Final sync to make sure all data is written
        subprocess.run("sync", shell=True)

        # Execute shutdown command
        subprocess.run(["sudo", "shutdown", "-h", "now"], shell=True)
    except Exception as e:
        logger.error(f"Failed to shutdown: {e}")


def schedule_wakeup(wake_time: datetime, debug: bool=False) -> None:
    try:
        epoch_time = int(wake_time.timestamp())
        logger.info(f"Scheduling wakeup at {wake_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if debug:
            logger.debug("Wakeup time set")
        subprocess.run(["sudo", "rtcwake", "-m", "no", "-t", str(epoch_time)], shell=True)
    except Exception as e:
        logger.error(f"Failed to schedule wakeup: {e}")
