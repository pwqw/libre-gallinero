#  +---------------------------------------------------+
#  |                                                   |
#  |   NodeMCU ESP-12E (ESP8266)                       |
#  |                                                   |
#  |  [ ] = Pin usado                                  |
#  |                                                   |
#  |  [3V3]----+-------------------+                   |
#  |           |                   |                   |
#  |         [D5] (GPIO14) <--- DHT11 DATA             |
#  |           |                   |                   |
#  |         [D1] (GPIO5)  <--- Relay 1 IN             |
#  |         [D2] (GPIO4)  <--- Relay 2 IN             |
#  |           |                   |                   |
#  |         [GND]----+-----------+---+                |
#  |                  |           |   |                |
#  |                Relay1      Relay2 DHT11 GND       |
#  |                GND         GND   GND              |
#  |                                                   |
#  |         [VIN] (5V)  ---> Relays VCC               |
#  |         [3V3]       ---> DHT11 VCC                |
#  |                                                   |
#  +---------------------------------------------------+
#  Pines usados:
#    D1 (GPIO5)  -> Relay 1 IN
#    D2 (GPIO4)  -> Relay 2 IN
#    D5 (GPIO14) -> DHT11 DATA
#    GND         -> GND relays y DHT11
#    VIN (5V)    -> VCC relays
#    3V3         -> VCC DHT11

import network
import ntptime
import time
import machine
import dht
from config import WIFI_SSID, WIFI_PASSWORD, load_wifi_config, save_wifi_config
from src.logic import compute_relay1_state, compute_relay2_state
from src.hotspot import hotspot_config_loop

# Pines (ajusta según tu hardware)
RELAY1_PIN = 5  # D1 en NodeMCU
RELAY2_PIN = 4  # D2 en NodeMCU
DHT_PIN = 14    # D5 en NodeMCU

TEMP_THRESHOLD = 30

relay1 = machine.Pin(RELAY1_PIN, machine.Pin.OUT)
relay2 = machine.Pin(RELAY2_PIN, machine.Pin.OUT)
dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))

# Función para conectar a WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        config = load_wifi_config()
        ssid = config['ssid'] if config else WIFI_SSID
        password = config['password'] if config else WIFI_PASSWORD
        wlan.connect(ssid, password)
        timeout = 0
        while not wlan.isconnected() and timeout < 15:
            time.sleep(1)
            timeout += 1
    return wlan.isconnected()

# Sincronizar hora con NTP
def sync_time():
    for _ in range(5):
        try:
            ntptime.settime()
            return True
        except:
            time.sleep(2)
    return False

# Obtener hora local
def get_local_time():
    tm = time.localtime()
    return tm[0], tm[1], tm[2], tm[3], tm[4]  # año, mes, día, hora, minuto

# Controlar relay 1 según amanecer/atardecer
def control_relay1():
    year, month, day, hour, minute = get_local_time()
    sunrise, sunset = calc_sun_times(year, month, day, LATITUDE)
    # Amanecer verano: 21 de diciembre
    sunrise_summer, _ = calc_sun_times(year, 12, 21, LATITUDE)
    # Atardecer verano: 21 de diciembre
    _, sunset_summer = calc_sun_times(year, 12, 21, LATITUDE)
    now_minutes = hour*60 + minute
    sunrise_today = sunrise[0]*60 + sunrise[1]
    sunset_today = sunset[0]*60 + sunset[1]
    sunrise_summer_m = sunrise_summer[0]*60 + sunrise_summer[1]
    sunset_summer_m = sunset_summer[0]*60 + sunset_summer[1]
    # Prender relay1 al amanecer de verano, apagar al amanecer real
    if sunrise_summer_m <= now_minutes < sunrise_today:
        relay1.value(1)
    elif sunrise_today <= now_minutes < sunset_today:
        relay1.value(0)
    # Prender relay1 al atardecer real, apagar al atardecer de verano
    elif sunset_today <= now_minutes < sunset_summer_m:
        relay1.value(1)
    else:
        relay1.value(0)

# Controlar relay 2 según temperatura
def control_relay2():
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        if temp > TEMP_THRESHOLD:
            relay2.value(1)  # Activa relay (apaga conexión)
        else:
            relay2.value(0)  # Normal abierto
    except Exception as e:
        print('Error leyendo DHT22:', e)

# Main loop
def main():
    if not connect_wifi():
        print('No se pudo conectar a WiFi. Iniciando hotspot de configuración...')
        hotspot_config_loop()
        return
    if not sync_time():
        print('No se pudo sincronizar la hora')
        return
    while True:
        control_relay1()
        control_relay2()
        time.sleep(30)

if __name__ == "__main__":
    main()