try:
    import ujson # type: ignore[import]
except ImportError:
    import json as ujson

# Configuración por defecto de ubicación para NodeMCU
LATITUDE = -31.4167  # Valor por defecto (Córdoba, Argentina)
LONGITUDE = -64.1833  # Valor por defecto (Córdoba, Argentina)

def load_wifi_config():
    try:
        with open('wifi_config.json', 'r') as f:
            return ujson.load(f)
    except Exception:
        return None

def save_wifi_config(ssid, password, hidden=False):
    with open('wifi_config.json', 'w') as f:
        ujson.dump({'ssid': ssid, 'password': password, 'hidden': hidden}, f)

def load_location_config():
    try:
        with open('location_config.json', 'r') as f:
            return ujson.load(f)
    except Exception:
        return {'latitude': LATITUDE, 'longitude': LONGITUDE}

def save_location_config(latitude, longitude):
    with open('location_config.json', 'w') as f:
        ujson.dump({'latitude': latitude, 'longitude': longitude}, f)
