from typing import Dict, TypedDict
from astral import LocationInfo
from astral.sun import sun
import datetime
from datetime import date, datetime
from dateutil.tz import tzlocal
import logging

logger = logging.getLogger(__name__)


def get_timezone() -> str:
    return tzlocal().tzname(datetime.now())


class SunStats(TypedDict):
    dawn: datetime
    sunrise: datetime
    noon: datetime
    sunset: datetime
    dusk: datetime


class TemporalLocation:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        region: str,
        city: str,
    ):
        self.city = city
        self.region = region
        self.latitude = latitude
        self.longitude = longitude

    @property
    def location(self) -> LocationInfo:
        self._location = LocationInfo(
            name=self.city,
            region=self.region,
            timezone=get_timezone(),
            latitude=self.latitude,
            longitude=self.longitude,
        )
        return self._location
    
    def get_sun_stats(self, date: date) -> SunStats:
        return TemporalLocation._get_sun_stats(self.location, date)

    @staticmethod
    def _get_sun_stats(location: LocationInfo, date: date) -> SunStats:
        return sun(location.observer, date=date) #type: ignore
