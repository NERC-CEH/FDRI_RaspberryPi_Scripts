from datetime import datetime

from raspberrycam.location import Location


def test_get_sun_stats() -> None:
    location = Location(55.8626453, -3.2031049)

    dt = datetime(2025, 6, 6, 16, 0)

    stats = location.get_sun_stats(dt)

    assert "sunrise" in stats and "sunset" in stats
    # We could go on to check for specific times
    # But would just be testing astral...
