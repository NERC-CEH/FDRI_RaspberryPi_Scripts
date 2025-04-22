import logging
from datetime import date, datetime
from typing import TypedDict

from astral import Observer
from astral.sun import sun
from dateutil.tz import tzlocal

logger = logging.getLogger(__name__)


def get_timezone() -> str:
    """Request the local timezone
    Returns:
        A string of the local timezone
    """
    return tzlocal().tzname(datetime.now())


class SunStats(TypedDict):
    """Typed dictionary of sun statistics used by Astral"""

    dawn: datetime
    sunrise: datetime
    noon: datetime
    sunset: datetime
    dusk: datetime


class Location(Observer):
    """Location object used to calculate sun statistics"""

    def __init__(self, latitude: float, longitude: float, *args, **kwargs):
        """
        Args:
            latitude: The location latitude
            longitude: The location longitude
        """
        super().__init__(*args, **kwargs, latitude=latitude, longitude=longitude)

    def get_sun_stats(self, date: date) -> SunStats:
        """Gets sun statistics at this location for a given date
        Args:
            date: The date to query
        Returns:
            A dictionary of sun statistics
        """

        return Location._get_sun_stats(self, date)

    @staticmethod
    def _get_sun_stats(observer: Observer, date: date) -> SunStats:
        """Gets sun statistics for a given obeserver and location
        Args:
            observer: An observer or location to query
            date: The date to query
        Returns:
            A dictionary of sun statistics
        """
        return sun(observer, date=date)  # type: ignore
