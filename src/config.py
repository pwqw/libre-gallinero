# config.py
# Configuración WiFi para NodeMCU

WIFI_SSID = "TU_SSID"
WIFI_PASSWORD = "TU_PASSWORD"

LATITUDE = -31.4167  # Valor por defecto (Córdoba, Argentina)
LONGITUDE = -64.1833  # Valor por defecto (Córdoba, Argentina)

def load_wifi_config():
    try:
        import ujson
        with open('wifi_config.json', 'r') as f:
            return ujson.load(f)
    except Exception:
        return None

def save_wifi_config(ssid, password):
    try:
        import ujson
        with open('wifi_config.json', 'w') as f:
            ujson.dump({'ssid': ssid, 'password': password}, f)
    except Exception:
        pass

def load_location_config():
    try:
        import ujson
        with open('location_config.json', 'r') as f:
            return ujson.load(f)
    except Exception:
        return {'latitude': LATITUDE, 'longitude': LONGITUDE}

def save_location_config(latitude, longitude):
    try:
        import ujson
        with open('location_config.json', 'w') as f:
            ujson.dump({'latitude': latitude, 'longitude': longitude}, f)
    except Exception:
        pass
