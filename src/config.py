# config.py
# Configuración WiFi para NodeMCU

WIFI_SSID = "TU_SSID"
WIFI_PASSWORD = "TU_PASSWORD"

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
