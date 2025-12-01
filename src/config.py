# config.py - Configuration loader
# Centralized module for loading .env configuration
import sys

# Constantes de configuración por defecto
DEFAULT_CONFIG = {
    'WIFI_SSID': 'libre gallinero',
    'WIFI_PASSWORD': 'huevos1',
    'WIFI_HIDDEN': 'false',
    'WEBREPL_PASSWORD': 'admin',
    'LATITUDE': '-31.4167',
    'LONGITUDE': '-64.1833',
    'APP': 'blink',
    'NTP_RESYNC_INTERVAL_SECONDS': '86400',  # 24 horas
    'MAX_TIME_DRIFT_SECONDS': '300'  # 5 minutos
}

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[config] {msg}")
    try:
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def parse_env(path):
    """
    Lee archivo .env y retorna dict de configuración
    
    Args:
        path: Ruta al archivo .env
        
    Returns:
        dict: Configuración parseada (vacío si no se puede leer)
    """
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
    """
    Carga configuración con cascada:
    1. .env (si existe)
    2. .env.example (si existe, copia a .env)
    3. DEFAULT_CONFIG (hardcoded)
    
    Returns:
        dict: Configuración cargada con valores por defecto si faltan
    """
    log("Cargando configuración...")
    cfg = {}
    
    # 1. Intentar cargar desde .env
    cfg = parse_env('.env')
    if cfg:
        log("Configuración cargada desde .env")
    else:
        # 2. Intentar cargar desde .env.example
        cfg = parse_env('.env.example')
        if cfg:
            log("Configuración cargada desde .env.example")
        else:
            # 3. Usar defaults
            log("Usando configuración por defecto")
            cfg = {}
    
    # Aplicar defaults para valores faltantes
    final_cfg = DEFAULT_CONFIG.copy()
    final_cfg.update(cfg)
    
    log(f"SSID configurado: {final_cfg.get('WIFI_SSID', 'N/A')}")
    log(f"App: {final_cfg.get('APP', 'N/A')}")
    return final_cfg

def get_webrepl_password():
    """
    Obtiene password WebREPL con prioridad:
    1. .env (WEBREPL_PASSWORD)
    2. webrepl_cfg.py (PASS)
    3. DEFAULT_CONFIG
    
    Returns:
        str: Password WebREPL
    """
    # 1. Intentar desde .env
    cfg = parse_env('.env')
    if cfg and 'WEBREPL_PASSWORD' in cfg:
        return cfg['WEBREPL_PASSWORD']
    
    # 2. Intentar desde webrepl_cfg.py
    try:
        import webrepl_cfg
        if hasattr(webrepl_cfg, 'PASS'):
            return webrepl_cfg.PASS
    except:
        pass
    
    # 3. Usar default
    return DEFAULT_CONFIG.get('WEBREPL_PASSWORD', 'admin')

