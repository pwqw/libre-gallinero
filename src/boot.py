# boot.py - Bootstrapping WiFi + WebREPL
# Versión minimalista sin hotspot (hotspot va en main.py)

try:
    import gc
    gc.collect()
except:
    pass

try:
    import network
    import webrepl
except ImportError:
    pass

import time

# Config por defecto
DEFAULT = {
    'WIFI_SSID': 'libre gallinero',
    'WIFI_PASSWORD': 'huevos1',
    'WIFI_HIDDEN': 'false',
    'WEBREPL_PASSWORD': 'admin',
    'LATITUDE': '-31.4167',
    'LONGITUDE': '-64.1833'
}

def parse_env(path):
    """Lee .env y retorna dict"""
    cfg = {}
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    except:
        pass
    return cfg

def load_config():
    """Carga config: .env -> .env.example -> DEFAULT"""
    # Intento 1: .env
    cfg = parse_env('.env')
    if cfg:
        print("[boot] .env OK")
        gc.collect()
        return cfg

    # Intento 2: copiar .env.example
    try:
        with open('.env.example', 'r') as src, open('.env', 'w') as dst:
            dst.write(src.read())
        cfg = parse_env('.env')
        if cfg:
            print("[boot] .env.example -> .env")
            gc.collect()
            return cfg
    except:
        pass

    print("[boot] DEFAULT")
    gc.collect()
    return DEFAULT

def setup_wifi(cfg, timeout=10):
    """Conecta WiFi. Retorna (ok, wlan, ip)"""
    ssid = cfg['WIFI_SSID']
    pw = cfg['WIFI_PASSWORD']
    hidden = cfg['WIFI_HIDDEN'].lower() == 'true'

    print("[boot] WiFi:", ssid)
    gc.collect()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        try:
            if hidden:
                wlan.connect(ssid, pw, -1)
            else:
                wlan.connect(ssid, pw)
        except TypeError:
            wlan.connect(ssid, pw)

        elapsed = 0
        while not wlan.isconnected() and elapsed < timeout:
            time.sleep(1)
            elapsed += 1

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("[boot] WiFi OK:", ip)
        gc.collect()
        return True, wlan, ip

    print("[boot] WiFi FAIL (main.py creará hotspot)")
    gc.collect()
    return False, wlan, None

def start_webrepl(cfg=None):
    """
    Inicia WebREPL con password explícito.
    Prioridad: cfg['WEBREPL_PASSWORD'] -> webrepl_cfg.py -> sin password
    """
    try:
        password = None
        
        # Intento 1: Password desde config (.env)
        if cfg and 'WEBREPL_PASSWORD' in cfg:
            password = cfg['WEBREPL_PASSWORD']
            print("[boot] WebREPL password desde .env")
        
        # Intento 2: webrepl_cfg.py (si no hay password en cfg)
        if not password:
            try:
                import webrepl_cfg
                password = webrepl_cfg.PASS
                print("[boot] WebREPL password desde webrepl_cfg.py")
            except:
                pass
        
        # Iniciar WebREPL con password (si existe)
        if password:
            webrepl.start(password=password)
        else:
            webrepl.start()
        
        print("[boot] WebREPL :8266")
        return True
    except Exception as e:
        print("[boot] WebREPL FAIL:", e)
        return False

# Boot sequence - Minimalista
def boot():
    """Bootstrap WiFi + WebREPL (SIEMPRE inicia WebREPL)"""
    try:
        print("\n=== boot.py ===")
        gc.collect()

        cfg = load_config()
        print("[boot] SSID:", cfg['WIFI_SSID'])
        gc.collect()

        ok, wlan, ip = setup_wifi(cfg)
        gc.collect()

        # IMPORTANTE: WebREPL se inicia SIEMPRE (WiFi OK o FAIL)
        # Si WiFi falla, main.py creará hotspot y WebREPL usará esa IP
        # Pasa cfg para usar password del .env si está disponible
        start_webrepl(cfg)

        if ok:
            print("[boot] WiFi OK:", ip)
            print("[boot] WebREPL activo en", ip, ":8266")
            print("[boot] Ejecuta: import main")
        else:
            print("[boot] WiFi FAIL")
            print("[boot] WebREPL activo (usará IP de hotspot)")
            print("[boot] main.py creará hotspot en 192.168.4.1")

        print("===\n")
        gc.collect()
    except Exception as e:
        import sys
        print("[boot] ERROR")
        sys.print_exception(e)
        gc.collect()

# Ejecutar
boot()
