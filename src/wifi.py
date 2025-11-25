# wifi.py - WiFi connection manager
_wlan = None
_cfg = None
_wdt_callback = None

def log(msg):
    print(f"[wifi] {msg}")
    try:
        import sys
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def _get_wlan():
    global _wlan
    if _wlan is None:
        import network
        _wlan = network.WLAN(network.STA_IF)
        _wlan.active(True)
    return _wlan

def _start_webrepl(ip):
    try:
        import webrepl
        webrepl.start()
        log(f"✅ WebREPL: ws://{ip}:8266")
    except:
        pass

def _check_ip_range(ip):
    if not ip.startswith('192.168.0.'):
        log(f"⚠ IP fuera de rango esperado (192.168.0.x)")

def connect_wifi(cfg, wdt_callback=None):
    global _cfg, _wdt_callback
    _cfg = cfg
    _wdt_callback = wdt_callback
    
    import network
    import time
    
    log("=== Iniciando conexión WiFi ===")
    wlan = _get_wlan()

    if wlan.isconnected():
        ifconfig = wlan.ifconfig()
        ip = ifconfig[0]
        if ip and ip != '0.0.0.0':
            log(f"WiFi ya conectado: {ip}")
            _check_ip_range(ip)
            _start_webrepl(ip)
        return True

    ssid = cfg['WIFI_SSID']
    pw = cfg['WIFI_PASSWORD']
    hidden = cfg.get('WIFI_HIDDEN', 'false').lower() == 'true'

    if isinstance(ssid, bytes):
        ssid = ssid.decode('utf-8')
    if isinstance(pw, bytes):
        pw = pw.decode('utf-8')
    
    log(f"Red: {repr(ssid)} (oculta: {hidden})")
    
    attempt = 0
    status_map = {1000: 'IDLE', 1001: 'CONNECTING', 1010: 'GOT_IP',
                  202: 'WRONG_PASSWORD', 201: 'NO_AP_FOUND', 200: 'CONNECT_FAIL'}
    
    while True:
        attempt += 1
        log(f"--- Intento #{attempt} ---")
        
        if wdt_callback:
            try:
                wdt_callback()
            except:
                pass
        
        if not hidden and (attempt == 1 or attempt % 5 == 0):
            try:
                networks = wlan.scan()
                found = any((net[0].decode('utf-8') if isinstance(net[0], bytes) else net[0]) == ssid for net in networks)
                if found:
                    log(f"✓ Red encontrada: {ssid}")
                else:
                    log(f"⚠ Red no encontrada, intentando conexión directa...")
            except:
                pass

        if wlan.status() == network.STAT_CONNECTING:
            wlan.disconnect()
            time.sleep(1)
        
        log(f"Conectando a {repr(ssid)}...")
        try:
            wlan.connect(ssid, pw)
        except Exception as e:
            log(f"✗ Error: {e}")
            time.sleep(5)
            continue

        timeout_s = 30 if hidden else 15
        log(f"Esperando conexión ({timeout_s}s)...")
        timeout = 0
        while not wlan.isconnected() and timeout < timeout_s:
            time.sleep(1)
            timeout += 1
            
            if wdt_callback and timeout % 5 == 0:
                try:
                    wdt_callback()
                except:
                    pass
            
            status = wlan.status()
            status_name = status_map.get(status, f'UNKNOWN({status})')
            
            if timeout % 5 == 0:
                log(f"Esperando... ({timeout}/{timeout_s}s) - {status_name}")
            
            if status in [202, 201, 200]:
                log(f"✗ Error: {status_name}")
                break

        if wlan.isconnected():
            time.sleep(0.5)
            ifconfig = wlan.ifconfig()
            ip = ifconfig[0]
            
            if ip == '0.0.0.0' or not ip:
                time.sleep(2)
                ifconfig = wlan.ifconfig()
                ip = ifconfig[0]
            
            if ip and ip != '0.0.0.0':
                log("✓✓✓ WiFi CONECTADO ✓✓✓")
                log(f"  IP: {ip}")
                log(f"  Gateway: {ifconfig[2]}")
                _check_ip_range(ip)
                log(f"  WebREPL: ws://{ip}:8266")
                _start_webrepl(ip)
                return True

        status = wlan.status()
        status_name = status_map.get(status, f'UNKNOWN({status})')
        log(f"✗ Intento #{attempt} falló - {status_name}")
        if wdt_callback:
            try:
                wdt_callback()
            except:
                pass
        time.sleep(5)

def monitor_wifi(check_interval=30):
    import time
    import network
    
    log(f"=== Monitoreo WiFi (cada {check_interval}s) ===")
    
    wlan = _get_wlan()
    last_ip = None
    disconnected_count = 0
    
    while True:
        try:
            if _wdt_callback:
                try:
                    _wdt_callback()
                except:
                    pass
            
            if wlan.isconnected():
                ifconfig = wlan.ifconfig()
                current_ip = ifconfig[0]
                
                if current_ip and current_ip != '0.0.0.0':
                    if last_ip != current_ip:
                        log(f"✓ WiFi: {current_ip} (Gateway: {ifconfig[2]})")
                        last_ip = current_ip
                    disconnected_count = 0
                else:
                    disconnected_count += 1
                    if disconnected_count >= 3:
                        log("⚠ IP inválida, reconectando...")
                        wlan.disconnect()
                        time.sleep(2)
                        if _cfg:
                            connect_wifi(_cfg, _wdt_callback)
            else:
                disconnected_count += 1
                if disconnected_count == 1:
                    log("⚠ WiFi desconectado, reconectando...")
                elif disconnected_count % 5 == 0:
                    log(f"⚠ WiFi desconectado ({disconnected_count} checks)")
                
                if disconnected_count >= 2:
                    wlan.disconnect()
                    time.sleep(2)
                    if _cfg:
                        connect_wifi(_cfg, _wdt_callback)
            
            time.sleep(check_interval)
            
        except Exception as e:
            log(f"⚠ Error monitoreo: {e}")
            time.sleep(check_interval)
