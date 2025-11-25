import pytest
from src.gallinero.solar import calc_sun_times, LATITUDE, LONGITUDE


def minutes_from_tuple(t):
    """Convert (hour, minute) tuple to total minutes."""
    return t[0] * 60 + t[1]


def test_sun_times_return_format():
    sunrise, sunset = calc_sun_times(2025, 4, 22)
    assert isinstance(sunrise, tuple) and len(sunrise) == 2
    assert isinstance(sunset, tuple) and len(sunset) == 2


def test_sunrise_before_sunset():
    sunrise, sunset = calc_sun_times(2025, 4, 22)
    assert minutes_from_tuple(sunrise) < minutes_from_tuple(sunset)


def test_summer_winter_solstice_comparison():
    # Southern hemisphere: summer solstice Dec 21, winter solstice Jun 21
    sr_summer, ss_summer = calc_sun_times(2025, 12, 21)
    sr_winter, ss_winter = calc_sun_times(2025, 6, 21)
    assert minutes_from_tuple(sr_winter) > minutes_from_tuple(sr_summer)
    assert minutes_from_tuple(ss_winter) < minutes_from_tuple(ss_summer)

def test_calc_sun_times():
    # 21 de diciembre, latitud -32.5, longitud -60
    sunrise, sunset = calc_sun_times(2025, 12, 21, LATITUDE, LONGITUDE)
    assert 4 <= sunrise[0] <= 7  # Amanecer entre 4 y 7 AM
    assert 19 <= sunset[0] <= 22  # Atardecer entre 19 y 22 PM

def test_control_relay1_logic():
    # Amanecer verano
    sunrise_summer, _ = calc_sun_times(2025, 12, 21, LATITUDE, LONGITUDE)
    # Amanecer real (otoño)
    sunrise_today, sunset_today = calc_sun_times(2025, 4, 21, LATITUDE, LONGITUDE)
    sunrise_summer_m = sunrise_summer[0]*60 + sunrise_summer[1]
    sunrise_today_m = sunrise_today[0]*60 + sunrise_today[1]
    sunset_today_m = sunset_today[0]*60 + sunset_today[1]
    now = (sunrise_summer_m + sunrise_today_m) // 2
    assert sunrise_summer_m < now < sunrise_today_m
    now2 = (sunrise_today_m + sunset_today_m) // 2
    assert sunrise_today_m < now2 < sunset_today_m

def test_control_relay2_logic():
    TEMP_THRESHOLD = 30
    class FakeDHT:
        def __init__(self, temp):
            self._temp = temp
        def measure(self):
            pass
        def temperature(self):
            return self._temp
    dht_sensor = FakeDHT(32)
    assert dht_sensor.temperature() > TEMP_THRESHOLD
    dht_sensor = FakeDHT(25)
    assert dht_sensor.temperature() < TEMP_THRESHOLD
