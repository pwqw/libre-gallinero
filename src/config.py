# config.py - Configuration loader
# Minimal module for loading .env configuration

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[config] {msg}")
    try:
        import sys
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def parse_env(path):
    """Lee .env"""
    cfg = {}
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        log(f"No se pudo leer {path}: {e}")
    return cfg

def load_config():
    """Carga config desde .env con defaults"""
    log("Cargando configuración...")
    cfg = parse_env('.env')
    if cfg:
        log("Configuración cargada desde .env")
    else:
        cfg = parse_env('.env.example')
        if cfg:
            log("Configuración cargada desde .env.example")
        else:
            log("Usando configuración por defecto")
            cfg = {
                'WIFI_SSID': 'libre gallinero',
                'WIFI_PASSWORD': 'huevos1',
                'WIFI_HIDDEN': 'false',
                'LATITUDE': '-31.4167',
                'LONGITUDE': '-64.1833',
                'PROJECT': 'heladera'
            }
    log(f"SSID configurado: {cfg.get('WIFI_SSID', 'N/A')}")
    log(f"Proyecto: {cfg.get('PROJECT', 'N/A')}")
    return cfg

