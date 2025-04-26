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

try:
    import network # type: ignore
    import ntptime # type: ignore
    import machine # type: ignore
    import dht # type: ignore
except ImportError:
    print("Error: Módulos de MicroPython no encontrados. Asegúrate de que estás ejecutando este script en un dispositivo compatible con MicroPython.")
import time
from config import WIFI_SSID, WIFI_PASSWORD, load_wifi_config, load_location_config
from logic import relay_ponedoras_state, relay_pollitos_state
from hotspot import hotspot_config_loop
from solar import calc_sun_times

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
    print('[WIFI] Intentando conectar...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        config = load_wifi_config()
        ssid = config['ssid'] if config else WIFI_SSID
        password = config['password'] if config else WIFI_PASSWORD
        print(f'[WIFI] Usando SSID: {ssid}')
        wlan.connect(ssid, password)
        timeout = 0
        while not wlan.isconnected() and timeout < 15:
            print(f'[WIFI] Esperando conexión... ({timeout+1}/15)')
            time.sleep(1)
            timeout += 1
    if wlan.isconnected():
        print('[WIFI] Conectado!')
    else:
        print('[WIFI] No se pudo conectar.')
    return wlan.isconnected()

# Sincronizar hora con NTP
def sync_time():
    print('[NTP] Sincronizando hora con NTP...')
    for intento in range(5):
        try:
            ntptime.settime()
            print('[NTP] Sincronización exitosa.')
            return True
        except Exception as e:
            print(f'[NTP] Fallo intento {intento+1}/5: {e}')
            time.sleep(2)
    print('[NTP] No se pudo sincronizar la hora.')
    return False

# Obtener hora local ajustada por zona horaria
def get_local_time():
    tm = time.localtime()
    # Ajuste de zona horaria según longitud (aprox. cada 15° = 1h)
    location = load_location_config()
    longitude = location.get('longitude', -60)
    tz_offset = int(round(longitude / 15))  # Por defecto, negativo en el hemisferio oeste
    hour = (tm[3] + tz_offset) % 24
    print(f'[TIME] Hora local: {tm[0]}-{tm[1]:02d}-{tm[2]:02d} {hour:02d}:{tm[4]:02d} (offset {tz_offset})')
    return tm[0], tm[1], tm[2], hour, tm[4]  # año, mes, día, hora local, minuto

# Controlar relay ponedoras según lógica solar y ubicación
def control_relay_ponedoras():
    year, month, day, hour, minute = get_local_time()
    location = load_location_config()
    latitude = location.get('latitude', -32.5)
    longitude = location.get('longitude', -60)
    # Amanecer y atardecer de verano (21 de diciembre)
    print(f'[RELAY1] Ubicación: lat={latitude}, lon={longitude}')
    sunrise_summer, sunset_summer = calc_sun_times(year, 12, 21, latitude, longitude)
    # Amanecer y atardecer de la fecha actual
    sunrise_today, sunset_today = calc_sun_times(year, month, day, latitude, longitude)
    # Convertir a minutos para lógica
    now_min = hour * 60 + minute
    sunrise_summer_min = sunrise_summer[0] * 60 + sunrise_summer[1]
    sunrise_today_min = sunrise_today[0] * 60 + sunrise_today[1]
    sunset_today_min = sunset_today[0] * 60 + sunset_today[1]
    sunset_summer_min = sunset_summer[0] * 60 + sunset_summer[1]
    estado = relay_ponedoras_state(now_min, sunrise_summer_min, sunrise_today_min, sunset_today_min, sunset_summer_min)
    print(f'[RELAY1] now={now_min} min, sunrise_today={sunrise_today_min}, sunset_today={sunset_today_min}, estado={estado}')
    relay1.value(estado)

# Controlar relay pollitos según temperatura
def control_relay_pollitos():
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        estado = relay_pollitos_state(temp)
        print(f'[RELAY2] Temperatura={temp}°C, estado={estado}')
        relay2.value(estado)
    except Exception as e:
        print('[RELAY2] Error leyendo DHT11:', e)

# Main loop
def main():
    print('[MAIN] Iniciando script principal...')
    if not connect_wifi():
        print('[MAIN] No se pudo conectar a WiFi. Iniciando hotspot de configuración...')
        hotspot_config_loop()
        return
    if not sync_time():
        print('[MAIN] No se pudo sincronizar la hora')
        return
    print('[MAIN] Entrando en bucle principal.')
    while True:
        control_relay_ponedoras()
        control_relay_pollitos()
        time.sleep(30)

if __name__ == "__main__":
    main()