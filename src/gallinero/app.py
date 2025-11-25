# Main application logic for gallinero (chicken coop)

import time
import gc
from solar import calc_sun_times
from logic import relay_ponedoras_state, relay_pollitos_state
import hardware

def get_local_time(cfg):
    """Hora local ajustada por zona"""
    tm = time.localtime()
    lon = float(cfg.get('LONGITUDE', -60))
    tz = int(round(lon / 15))
    hour = (tm[3] + tz) % 24
    return tm[0], tm[1], tm[2], hour, tm[4]

def control_ponedoras(cfg):
    """Control relay ponedoras (solar)"""
    if hardware.relay1 is None:
        return
    year, month, day, hour, minute = get_local_time(cfg)
    lat = float(cfg.get('LATITUDE', -32.5))
    lon = float(cfg.get('LONGITUDE', -60))

    sunrise_summer, sunset_summer = calc_sun_times(year, 12, 21, lat, lon)
    sunrise_today, sunset_today = calc_sun_times(year, month, day, lat, lon)

    now_min = hour * 60 + minute
    sunrise_summer_min = sunrise_summer[0] * 60 + sunrise_summer[1]
    sunrise_today_min = sunrise_today[0] * 60 + sunrise_today[1]
    sunset_today_min = sunset_today[0] * 60 + sunset_today[1]
    sunset_summer_min = sunset_summer[0] * 60 + sunset_summer[1]

    estado = relay_ponedoras_state(now_min, sunrise_summer_min, sunrise_today_min, sunset_today_min, sunset_summer_min)
    hardware.relay1.value(estado)
    print(f'[R1] now={now_min}, estado={estado}')

def control_pollitos():
    """Control relay pollitos (temperatura)"""
    if hardware.dht_sensor is None or hardware.relay2 is None:
        return
    try:
        hardware.dht_sensor.measure()
        temp = hardware.dht_sensor.temperature()
        estado = relay_pollitos_state(temp)
        hardware.relay2.value(estado)
        print(f'[R2] temp={temp}°C, estado={estado}')
    except Exception as e:
        print('[R2] DHT error:', e)

def run(cfg):
    """Main control loop for gallinero"""
    print('\n=== gallinero/app.py ===')
    gc.collect()
    
    # Initialize hardware
    hardware.init_hardware()
    
    print('[gallinero] Loop principal...')
    while True:
        control_ponedoras(cfg)
        control_pollitos()
        gc.collect()
        time.sleep(30)

