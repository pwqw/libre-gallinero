# Hardware initialization and control for gallinero app
#
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
    import machine
    import dht
    import gc
except ImportError:
    print("[gallinero/hardware] ERROR: Módulos MicroPython no encontrados")

# Hardware pins
RELAY1_PIN = 5   # D1 - Ponedoras
RELAY2_PIN = 4   # D2 - Pollitos
DHT_PIN = 14     # D5

# Global hardware objects
relay1 = None
relay2 = None
dht_sensor = None

def init_hardware():
    """Initialize hardware (relays and DHT sensor)"""
    global relay1, relay2, dht_sensor
    
    try:
        relay1 = machine.Pin(RELAY1_PIN, machine.Pin.OUT)
        relay2 = machine.Pin(RELAY2_PIN, machine.Pin.OUT)
        print('[gallinero/hardware] Relays inicializados')
        gc.collect()
    except Exception as e:
        print('[gallinero/hardware] Error inicializando relays:', e)
        relay1 = None
        relay2 = None
    
    try:
        dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))
        print('[gallinero/hardware] DHT inicializado')
        gc.collect()
    except Exception as e:
        print('[gallinero/hardware] DHT no disponible (continuando sin sensor):', e)
        dht_sensor = None
        gc.collect()
    
    return relay1, relay2, dht_sensor

