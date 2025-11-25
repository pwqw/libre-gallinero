# wifi.py - WiFi connection manager
# Minimal module for WiFi connectivity

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[wifi] {msg}")
    try:
        import sys
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def connect_wifi(cfg):
    """
    Conecta WiFi en loop hasta que tenga éxito.
    Intenta conectarse indefinidamente hasta lograr conexión.
    """
    import network
    import time
    
    log("=== Iniciando conexión WiFi ===")
    
    wlan = network.WLAN(network.STA_IF)
    log("Interfaz WiFi STA creada")
    
    wlan.active(True)
    log("Interfaz WiFi activada")

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        log(f"WiFi ya conectado: {ip}")
        log(f"Gateway: {wlan.ifconfig()[2]}")
        log(f"DNS: {wlan.ifconfig()[3]}")
        return True

    ssid = cfg['WIFI_SSID']
    pw = cfg['WIFI_PASSWORD']
    hidden = cfg.get('WIFI_HIDDEN', 'false').lower() == 'true'

    if isinstance(ssid, bytes):
        ssid = ssid.decode('utf-8')
    if isinstance(pw, bytes):
        pw = pw.decode('utf-8')
    
    log(f"Buscando red: {repr(ssid)}")
    log(f"Red oculta: {hidden}")
    log(f"Longitud SSID: {len(ssid)} caracteres")
    log(f"Longitud password: {len(pw)} caracteres")
    log("Modo: Reintentos infinitos hasta conexión exitosa")
    
    attempt = 0
    
    while True:
        attempt += 1
        log("")
        log(f"--- Intento de conexión #{attempt} ---")
        
        if not hidden:
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

        if wlan.status() == network.STAT_CONNECTING:
            log("Limpiando estado de conexión anterior...")
            wlan.disconnect()
            time.sleep(1)
        
        log(f"Intentando conectar a {repr(ssid)}...")
        try:
            if hidden:
                log("Usando método de conexión para red oculta...")
                wlan.connect(ssid, pw, bssid=-1)
                log("Comando de conexión enviado (red oculta, bssid=-1)")
            else:
                wlan.connect(ssid, pw)
                log("Comando de conexión enviado")
        except TypeError as e:
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
            
            if status in [202, 201, 200]:
                log(f"✗ Estado de error detectado: {status_name}")
                break

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

