# Hardware initialization and control for gallinero app

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

