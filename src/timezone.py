# timezone.py - Timezone utilities for all apps
# Calculates timezone offset from longitude
import sys

def log(msg):
    """Log with module prefix"""
    print(f'[timezone] {msg}')
    try:
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def get_timezone_offset(longitude):
    """
    Calculate timezone offset from longitude.

    Args:
        longitude: Longitude in degrees (-180 to 180)
                  Negative = West, Positive = East

    Returns:
        int: Timezone offset in hours from UTC

    Examples:
        -64.1833 (Córdoba, Argentina) → -4 hours
        -60.0 (Uruguay) → -4 hours
        0.0 (Greenwich) → 0 hours
        120.0 (China) → 8 hours
    """
    # Timezone = longitude / 15 degrees per hour
    # Round to nearest hour for simplicity
    return int(round(longitude / 15.0))

def apply_timezone_to_time(time_tuple, tz_offset):
    """
    Apply timezone offset to a time tuple.

    Args:
        time_tuple: (year, month, day, hour, minute, second, weekday, yearday)
        tz_offset: Timezone offset in hours

    Returns:
        tuple: Modified time tuple with adjusted hour
    """
    year, month, day, hour, minute, second, weekday, yearday = time_tuple

    # Apply timezone offset
    hour = (hour + tz_offset) % 24

    return (year, month, day, hour, minute, second, weekday, yearday)
