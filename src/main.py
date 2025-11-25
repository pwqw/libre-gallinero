# main.py - Generic WiFi Manager + Project Loader
# Reusable across different projects (gallinero, heladera, etc.)

import sys
import time

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[main] {msg}")
    sys.stdout.flush()

log("=== Iniciando main.py ===")

# Estado: Importando módulos
try:
    import network
    log("Módulo network importado")
except ImportError as e:
    log(f"ERROR: network no encontrado: {e}")

try:
    import ntptime
    log("Módulo ntptime importado")
except ImportError as e:
    log(f"ERROR: ntptime no encontrado: {e}")

try:
    import machine
    log("Módulo machine importado")
except ImportError as e:
    log(f"ERROR: machine no encontrado: {e}")

try:
    import gc
    gc.collect()
    log("GC inicializado y limpiado")
except ImportError as e:
    log(f"ERROR: gc no encontrado: {e}")

# === CONFIGURACIÓN ===
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
                'PROJECT': 'gallinero'  # Default project
            }
    log(f"SSID configurado: {cfg.get('WIFI_SSID', 'N/A')}")
    log(f"Proyecto: {cfg.get('PROJECT', 'N/A')}")
    return cfg

# === WIFI + NTP ===
def connect_wifi(cfg):
    """
    Conecta WiFi siguiendo lógica:
    1. Busca red por SSID
    2. Intenta conectar con password
    3. Si falla, retorna False
    """
    log("=== Iniciando conexión WiFi ===")
    
    # Estado: Activando interfaz WiFi
    wlan = network.WLAN(network.STA_IF)
    log("Interfaz WiFi STA creada")
    
    wlan.active(True)
    log("Interfaz WiFi activada")

    # Estado: Verificando conexión existente
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        log(f"WiFi ya conectado: {ip}")
        log(f"Gateway: {wlan.ifconfig()[2]}")
        log(f"DNS: {wlan.ifconfig()[3]}")
        return True

    ssid = cfg['WIFI_SSID']
    pw = cfg['WIFI_PASSWORD']
    hidden = cfg.get('WIFI_HIDDEN', 'false').lower() == 'true'

    log(f"Buscando red: {ssid}")
    log(f"Red oculta: {hidden}")
    
    # Estado: Escaneando redes
    log("Escaneando redes disponibles...")
    try:
        networks = wlan.scan()
        log(f"Encontradas {len(networks)} redes")
        found = False
        for net in networks:
            net_ssid = net[0].decode('utf-8') if isinstance(net[0], bytes) else net[0]
            if net_ssid == ssid:
                found = True
                log(f"✓ Red encontrada: {ssid} (RSSI: {net[3]} dBm)")
                break
        
        if not found and not hidden:
            log(f"⚠ Red no encontrada en escaneo: {ssid}")
            log("Intentando conexión directa (puede ser red oculta)...")
    except Exception as e:
        log(f"Error escaneando redes: {e}")

    # Estado: Intentando conectar
    log(f"Intentando conectar a {ssid}...")
    try:
        if hidden:
            wlan.connect(ssid, pw, -1)
            log("Comando de conexión enviado (red oculta)")
        else:
            wlan.connect(ssid, pw)
            log("Comando de conexión enviado")
    except TypeError:
        wlan.connect(ssid, pw)
        log("Comando de conexión enviado (fallback)")
    except Exception as e:
        log(f"✗ Error al conectar: {e}")
        return False

    # Estado: Esperando conexión
    log("Esperando conexión (timeout: 15s)...")
    timeout = 0
    while not wlan.isconnected() and timeout < 15:
        time.sleep(1)
        timeout += 1
        if timeout % 3 == 0:
            log(f"Esperando conexión... ({timeout}/15s)")

    # Estado: Verificando resultado
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        gateway = wlan.ifconfig()[2]
        dns = wlan.ifconfig()[3]
        log(f"✓ WiFi conectado exitosamente")
        log(f"  IP: {ip}")
        log(f"  Máscara: {wlan.ifconfig()[1]}")
        log(f"  Gateway: {gateway}")
        log(f"  DNS: {dns}")
        log(f"  WebREPL: ws://{ip}:8266")
        log("=== Conexión WiFi exitosa ===")
        return True

    log(f"✗ WiFi FAIL - No se pudo conectar a {ssid}")
    log("=== Fallo de conexión WiFi ===")
    return False

def sync_ntp():
    """Sincroniza NTP"""
    log("=== Sincronizando hora NTP ===")
    
    # Estado: Obteniendo hora actual antes de sync
    try:
        import utime
        tm_before = utime.localtime()
        log(f"Hora actual (antes): {tm_before[3]:02d}:{tm_before[4]:02d}:{tm_before[5]:02d}")
    except:
        pass
    
    for i in range(5):
        try:
            log(f"Intento NTP {i+1}/5...")
            ntptime.settime()
            
            # Estado: Verificando hora después de sync
            try:
                tm_after = utime.localtime()
                log(f"Hora sincronizada: {tm_after[3]:02d}:{tm_after[4]:02d}:{tm_after[5]:02d}")
                log(f"Fecha: {tm_after[2]:02d}/{tm_after[1]:02d}/{tm_after[0]}")
            except:
                pass
            
            log("✓ NTP sincronizado exitosamente")
            log("=== Sincronización NTP completada ===")
            return True
        except Exception as e:
            log(f"✗ NTP intento {i+1}/5 falló: {e}")
            if i < 4:
                time.sleep(2)
    
    log("✗ NTP FAIL - No se pudo sincronizar después de 5 intentos")
    log("=== Fallo de sincronización NTP ===")
    return False

# === PROJECT LOADER ===
def load_project(project_name, cfg):
    """Load and run project-specific code"""
    log("=== Cargando proyecto ===")
    log(f"Proyecto: {project_name}")
    gc.collect()
    log(f"Memoria libre después de GC: {gc.mem_free()} bytes")
    
    try:
        if project_name == 'gallinero':
            log("Importando módulo gallinero...")
            import gallinero
            log("Módulo gallinero importado")
            log("Ejecutando gallinero.run()...")
            gallinero.run(cfg)
        elif project_name == 'heladera':
            log("Importando módulo heladera...")
            import heladera
            log("Módulo heladera importado")
            log("Ejecutando heladera.blink_led()...")
            heladera.blink_led()
        else:
            log(f"✗ Proyecto desconocido: {project_name}")
            log("Proyectos disponibles: gallinero, heladera")
    except ImportError as e:
        log(f"✗ Error importando proyecto {project_name}: {e}")
        log("Asegúrate de que el módulo existe en src/")
    except Exception as e:
        log(f"✗ Error ejecutando proyecto {project_name}: {e}")
        import sys
        sys.print_exception(e)

# === MAIN LOOP ===
def main():
    """Función principal - DEBE ejecutarse manualmente vía WebREPL: import main"""
    log("")
    log("=" * 50)
    log("Iniciando función main()")
    log("=" * 50)
    
    # Estado: Memoria inicial
    gc.collect()
    log(f"Memoria libre inicial: {gc.mem_free()} bytes")
    
    # Estado: Cargando configuración
    cfg = load_config()
    project = cfg.get('PROJECT', 'gallinero')
    log(f"Configuración cargada")
    log(f"  SSID: {cfg.get('WIFI_SSID', 'N/A')}")
    log(f"  Proyecto: {project}")
    log(f"  Latitud: {cfg.get('LATITUDE', 'N/A')}")
    log(f"  Longitud: {cfg.get('LONGITUDE', 'N/A')}")
    gc.collect()
    log(f"Memoria libre después de cargar config: {gc.mem_free()} bytes")

    # Estado: Conectando WiFi
    wifi_connected = connect_wifi(cfg)
    if not wifi_connected:
        log("✗ No se pudo conectar a WiFi")
        log("El dispositivo no puede continuar sin conexión WiFi")
        log("Verifica la configuración de red y reinicia")
        return

    # Estado: Sincronizando hora
    ntp_synced = sync_ntp()
    if not ntp_synced:
        log("⚠ Sin NTP, reloj puede estar desincronizado")
    gc.collect()
    log(f"Memoria libre después de WiFi/NTP: {gc.mem_free()} bytes")

    # Estado: Cargando proyecto
    log("")
    log("=" * 50)
    log("Iniciando carga de proyecto")
    log("=" * 50)
    load_project(project, cfg)

# IMPORTANTE: main.py NO se ejecuta automáticamente
# Para iniciar manualmente vía WebREPL:
#   >>> import main
#   >>> main.main()
# O simplemente:
#   >>> from main import main; main()
#
# Esto garantiza que WebREPL siempre esté disponible después de boot.py
