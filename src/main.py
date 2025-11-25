# main.py - Generic WiFi Manager + Project Loader
# Reusable across different projects (gallinero, heladera, etc.)

import sys
import time

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[main] {msg}")
    # En MicroPython, sys.stdout puede ser uio.FileIO sin flush()
    if hasattr(sys.stdout, 'flush'):
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
    Conecta WiFi en loop hasta que tenga éxito.
    Intenta conectarse indefinidamente hasta lograr conexión.
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

    # Asegurar que SSID y password son strings (no bytes)
    if isinstance(ssid, bytes):
        ssid = ssid.decode('utf-8')
    if isinstance(pw, bytes):
        pw = pw.decode('utf-8')
    
    log(f"Buscando red: {repr(ssid)}")  # repr() muestra caracteres especiales
    log(f"Red oculta: {hidden}")
    log(f"Longitud SSID: {len(ssid)} caracteres")
    log(f"Longitud password: {len(pw)} caracteres")
    log("Modo: Reintentos infinitos hasta conexión exitosa")
    
    attempt = 0
    
    # Loop infinito hasta conectar
    while True:
        attempt += 1
        log("")
        log(f"--- Intento de conexión #{attempt} ---")
        
        # Para redes ocultas, no escaneamos (ahorra tiempo y evita problemas)
        if not hidden:
            # Estado: Escaneando redes (cada 5 intentos para ahorrar tiempo)
            if attempt == 1 or attempt % 5 == 0:
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
                    
                    if not found:
                        log(f"⚠ Red no encontrada en escaneo: {ssid}")
                        log("Intentando conexión directa (puede ser red oculta)...")
                except Exception as e:
                    log(f"Error escaneando redes: {e}")
        else:
            log("Red oculta detectada - saltando escaneo")

        # Estado: Limpiar conexión anterior si existe
        if wlan.status() == network.STAT_CONNECTING:
            log("Limpiando estado de conexión anterior...")
            wlan.disconnect()
            time.sleep(1)
        
        # Estado: Intentando conectar
        log(f"Intentando conectar a {repr(ssid)}...")
        try:
            if hidden:
                # Para redes ocultas, usar bssid=-1 explícitamente
                log("Usando método de conexión para red oculta...")
                wlan.connect(ssid, pw, bssid=-1)
                log("Comando de conexión enviado (red oculta, bssid=-1)")
            else:
                wlan.connect(ssid, pw)
                log("Comando de conexión enviado")
        except TypeError as e:
            # Fallback: intentar sin bssid
            log(f"TypeError en connect: {e}")
            log("Intentando conexión sin bssid...")
            try:
                wlan.connect(ssid, pw)
                log("Comando de conexión enviado (fallback sin bssid)")
            except Exception as e2:
                log(f"✗ Error en fallback: {e2}")
                log("Reintentando en 5 segundos...")
                time.sleep(5)
                continue
        except Exception as e:
            log(f"✗ Error al conectar: {e}")
            log(f"Tipo de error: {type(e).__name__}")
            log("Reintentando en 5 segundos...")
            time.sleep(5)
            continue

        # Estado: Esperando conexión (timeout más largo para redes ocultas)
        timeout_seconds = 30 if hidden else 15
        log(f"Esperando conexión (timeout: {timeout_seconds}s)...")
        timeout = 0
        while not wlan.isconnected() and timeout < timeout_seconds:
            time.sleep(1)
            timeout += 1
            status = wlan.status()
            status_names = {
                1000: 'STAT_IDLE',
                1001: 'STAT_CONNECTING',
                1010: 'STAT_GOT_IP',
                202: 'STAT_WRONG_PASSWORD',
                201: 'STAT_NO_AP_FOUND',
                200: 'STAT_CONNECT_FAIL'
            }
            status_name = status_names.get(status, f'STAT_UNKNOWN({status})')
            
            if timeout % 5 == 0:
                log(f"Esperando conexión... ({timeout}/{timeout_seconds}s) - Estado: {status_name}")
            
            # Si el estado indica error, salir del loop de espera
            if status in [202, 201, 200]:
                log(f"✗ Estado de error detectado: {status_name}")
                break

        # Estado: Verificando resultado
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            gateway = wlan.ifconfig()[2]
            dns = wlan.ifconfig()[3]
            log("")
            log("✓✓✓ WiFi CONECTADO EXITOSAMENTE ✓✓✓")
            log(f"  IP: {ip}")
            log(f"  Máscara: {wlan.ifconfig()[1]}")
            log(f"  Gateway: {gateway}")
            log(f"  DNS: {dns}")
            log(f"  WebREPL: ws://{ip}:8266")
            log(f"  Intentos necesarios: {attempt}")
            log("=== Conexión WiFi exitosa ===")
            return True

        # Si no conectó, mostrar estado y esperar antes de reintentar
        status = wlan.status()
        status_names = {
            1000: 'STAT_IDLE',
            1001: 'STAT_CONNECTING',
            1010: 'STAT_GOT_IP',
            202: 'STAT_WRONG_PASSWORD',
            201: 'STAT_NO_AP_FOUND',
            200: 'STAT_CONNECT_FAIL'
        }
        status_name = status_names.get(status, f'STAT_UNKNOWN({status})')
        log(f"✗ Intento #{attempt} falló - Estado: {status_name}")
        if status == 202:
            log("⚠ Posible error de contraseña - verifica WIFI_PASSWORD en .env")
        elif status == 201:
            log("⚠ Red no encontrada - verifica WIFI_SSID y WIFI_HIDDEN en .env")
        elif status == 200:
            log("⚠ Fallo de conexión - verifica que la red esté disponible")
        log("Reintentando en 5 segundos...")
        time.sleep(5)

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
    """
    Load and run project-specific code (OPCIONAL)
    Si el módulo no existe, simplemente no lo carga y continúa.
    Esto permite que el setup inicial funcione sin los módulos del proyecto.
    """
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
            log(f"⚠ Proyecto desconocido: {project_name}")
            log("Proyectos disponibles: gallinero, heladera")
            log("Continuando sin cargar proyecto...")
    except ImportError as e:
        log(f"⚠ Módulo {project_name} no encontrado: {e}")
        log("Esto es normal durante el setup inicial.")
        log("El módulo se instalará durante el deploy por WiFi.")
        log("Sistema funcionando en modo básico (WiFi + WebREPL)")
    except Exception as e:
        log(f"✗ Error ejecutando proyecto {project_name}: {e}")
        import sys
        sys.print_exception(e)
        log("Continuando sin proyecto...")

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

    # Estado: Conectando WiFi (loop hasta éxito)
    log("Iniciando conexión WiFi (reintentos infinitos)...")
    connect_wifi(cfg)  # Esta función no retorna hasta conectar exitosamente

    # Estado: Sincronizando hora
    ntp_synced = sync_ntp()
    if not ntp_synced:
        log("⚠ Sin NTP, reloj puede estar desincronizado")
    gc.collect()
    log(f"Memoria libre después de WiFi/NTP: {gc.mem_free()} bytes")

    # Estado: Cargando proyecto (OPCIONAL - solo si existe)
    log("")
    log("=" * 50)
    log("Iniciando carga de proyecto (opcional)")
    log("=" * 50)
    try:
        load_project(project, cfg)
        log("✅ Proyecto cargado exitosamente")
    except Exception as e:
        log(f"⚠ No se pudo cargar el proyecto: {e}")
        log("Sistema funcionando en modo básico (WiFi + WebREPL disponible)")
        log("Puedes cargar el proyecto más tarde vía WebREPL o deploy")

# Ejecutar main() automáticamente después de un delay para asegurar que WebREPL esté listo
# El delay permite que WebREPL se inicie completamente antes de comenzar WiFi
log("Esperando 2 segundos para que WebREPL se inicie completamente...")
time.sleep(2)
log("Iniciando main() automáticamente...")
try:
    main()
except Exception as e:
    log(f"Error en main(): {e}")
    import sys
    sys.print_exception(e)
    log("El sistema seguirá funcionando, pero WiFi no se conectará automáticamente")
    log("Puedes ejecutar manualmente: import main; main.main()")
