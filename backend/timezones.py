"""
file with the most common timezones for the world.
"""

import datetime
import re
from zoneinfo import ZoneInfo

COMMON_TIMEZONES = [
    # Africa
    "Africa/Cairo",
    "Africa/Casablanca",
    "Africa/Johannesburg",
    "Africa/Lagos",
    "Africa/Nairobi",
    
    # Americas (North & South)
    "America/Anchorage",
    "America/Bogota",
    "America/Buenos_Aires",
    "America/Caracas",
    "America/Chicago",
    "America/Denver",
    "America/Detroit",
    "America/Edmonton",
    "America/Guatemala",
    "America/Halifax",
    "America/Havana",
    "America/Lima",
    "America/Los_Angeles",
    "America/Mexico_City",
    "America/Miami",
    "America/New_York",
    "America/Phoenix",
    "America/Santiago",
    "America/Sao_Paulo",
    "America/Toronto",
    "America/Vancouver",
    "America/Winnipeg",
    
    # Asia
    "Asia/Almaty",
    "Asia/Anadyr",
    "Asia/Baghdad",
    "Asia/Bangkok",
    "Asia/Beijing",
    "Asia/Dhaka",
    "Asia/Dubai",
    "Asia/Hong_Kong",
    "Asia/Jakarta",
    "Asia/Jerusalem",
    "Asia/Kabul",
    "Asia/Karachi",
    "Asia/Kolkata",
    "Asia/Kuala_Lumpur",
    "Asia/Manila",
    "Asia/Riyadh",
    "Asia/Seoul",
    "Asia/Shanghai",
    "Asia/Singapore",
    "Asia/Taipei",
    "Asia/Tashkent",
    "Asia/Tehran",
    "Asia/Tokyo",
    
    # Atlantic & Pacific
    "Atlantic/Reykjavik",
    "Pacific/Auckland",
    "Pacific/Chatham",
    "Pacific/Fiji",
    "Pacific/Honolulu",
    "Pacific/Pago_Pago",
    
    # Europe
    "Europe/Amsterdam",
    "Europe/Athens",
    "Europe/Belgrade",
    "Europe/Berlin",
    "Europe/Brussels",
    "Europe/Bucharest",
    "Europe/Budapest",
    "Europe/Copenhagen",
    "Europe/Dublin",
    "Europe/Helsinki",
    "Europe/Istanbul",
    "Europe/Lisbon",
    "Europe/London",
    "Europe/Madrid",
    "Europe/Moscow",
    "Europe/Oslo",
    "Europe/Paris",
    "Europe/Prague",
    "Europe/Rome",
    "Europe/Stockholm",
    "Europe/Vienna",
    "Europe/Warsaw",
    "Europe/Zurich",
    
    # Indian Ocean & Australia
    "Indian/Maldives",
    "Australia/Adelaide",
    "Australia/Brisbane",
    "Australia/Darwin",
    "Australia/Melbourne",
    "Australia/Perth",
    "Australia/Sydney",
    
    # Baseline
    "UTC"
]


def normalize_timezone_name(value: str) -> str:
    """Normalize a timezone string from user input to a canonical IANA name."""
    if not value:
        return value

    cleaned = value.strip()
    if cleaned in COMMON_TIMEZONES:
        return cleaned

    normalized = cleaned.replace(" ", "_")
    if normalized in COMMON_TIMEZONES:
        return normalized

    compact = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned).strip("_")
    for candidate in COMMON_TIMEZONES:
        if candidate.lower().endswith(compact.lower()):
            return candidate

    return cleaned


def get_local_scheduled_datetime(
    hour: int,
    minute: int,
    now: datetime.datetime | None = None,
    timezone_name: str | None = None,
) -> datetime.datetime:
    """Build a timezone-aware datetime for the requested local hour/minute."""
    current_time = now or datetime.datetime.now().astimezone()
    tzinfo = current_time.tzinfo or datetime.timezone.utc

    if timezone_name:
        normalized_timezone = normalize_timezone_name(timezone_name)
        tzinfo = ZoneInfo(normalized_timezone)

    return datetime.datetime.combine(
        current_time.date(),
        datetime.time(hour=hour, minute=minute, tzinfo=tzinfo),
    )