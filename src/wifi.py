# wifi.py - WiFi connection manager
import sys

_wlan = None
_cfg = None
_wdt_callback = None

def log(msg):
    print(f"[wifi] {msg}")
    try:
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

def _reset_wlan():
    global _wlan
    import network
    import time
    if _wlan is not None:
        try:
            if _wlan.isconnected():
                _wlan.disconnect()
            _wlan.active(False)
            time.sleep(0.5)
        except:
            pass
    _wlan = network.WLAN(network.STA_IF)
    _wlan.active(True)
    time.sleep(0.5)
    return _wlan

def _start_ap_fallback(cfg):
    try:
        import network
        ap = network.WLAN(network.AP_IF)
        ap_password = cfg.get('WIFI_PASSWORD', '1234')
        if not ap_password or ap_password.strip() == '':
            ap_password = '1234'
        if isinstance(ap_password, bytes):
            ap_password = ap_password.decode('utf-8')
        ap.active(True)
        ap.config(essid='Gallinero-Setup', password=ap_password)
        ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
        log("📡 Hotspot: Gallinero-Setup")
        log("   IP: 192.168.4.1")
        _start_webrepl('192.168.4.1')
        return True
    except Exception as e:
        log(f"✗ AP error: {e}")
        return False

def _start_webrepl(ip):
    try:
        import webrepl
        import gc
        webrepl.start()
        log(f"✅ WebREPL: ws://{ip}:8266")
        try:
            if hasattr(sys.stdout, 'flush'):
                sys.stdout.flush()
        except:
            pass
        gc.collect()
        log(f"Mem: {gc.mem_free()} bytes")
    except:
        pass

def _check_ip_range(ip):
    if not ip.startswith('192.168.0.'):
        log(f"⚠ IP fuera rango")

def _wdt_feed():
    if _wdt_callback:
        try:
            _wdt_callback()
        except:
            pass

def connect_wifi(cfg, wdt_callback=None):
    global _cfg, _wdt_callback
    _cfg = cfg
    _wdt_callback = wdt_callback
    import network
    import time
    log("=== WiFi ===")
    wlan = _get_wlan()
    if wlan.isconnected():
        ifconfig = wlan.ifconfig()
        ip = ifconfig[0]
        if ip and ip != '0.0.0.0':
            log(f"WiFi conectado: {ip}")
            _check_ip_range(ip)
            _start_webrepl(ip)
            try:
                ap = network.WLAN(network.AP_IF)
                if ap.active():
                    ap.active(False)
            except:
                pass
        return True
    ssid = cfg.get('WIFI_SSID', '').strip()
    pw = cfg.get('WIFI_PASSWORD', '').strip()
    hidden = cfg.get('WIFI_HIDDEN', 'false').lower() == 'true'
    if not ssid or ssid == '':
        log("⚠ No WiFi config")
        log("📡 Activando hotspot...")
        _start_ap_fallback(cfg)
        return False
    if isinstance(ssid, bytes):
        ssid = ssid.decode('utf-8')
    if isinstance(pw, bytes):
        pw = pw.decode('utf-8')
    log(f"Red: {repr(ssid)} (oculta: {hidden})")
    max_attempts = 3
    attempt = 0
    status_map = {1000: 'IDLE', 1001: 'CONNECTING', 1010: 'GOT_IP',
                  202: 'WRONG_PASSWORD', 201: 'NO_AP_FOUND', 200: 'CONNECT_FAIL'}
    while attempt < max_attempts:
        attempt += 1
        log(f"--- Intento #{attempt}/{max_attempts} ---")
        _wdt_feed()
        if not hidden and (attempt == 1 or attempt % 5 == 0):
            try:
                networks = wlan.scan()
                found = any((net[0].decode('utf-8') if isinstance(net[0], bytes) else net[0]) == ssid for net in networks)
                if found:
                    log(f"✓ Red: {ssid}")
                else:
                    log(f"⚠ Red no encontrada...")
            except:
                pass
        if wlan.status() == network.STAT_CONNECTING:
            wlan.disconnect()
            time.sleep(1)
        if attempt > 1 and attempt % 3 == 0:
            log("🔄 Reset WiFi...")
            wlan = _reset_wlan()
            time.sleep(1)
        log(f"Conectando a {repr(ssid)}...")
        try:
            wlan.connect(ssid, pw)
        except Exception as e:
            log(f"✗ Error: {e}")
            time.sleep(5)
            continue
        timeout_s = 30 if hidden else 15
        log(f"Esperando ({timeout_s}s)...")
        timeout = 0
        while not wlan.isconnected() and timeout < timeout_s:
            time.sleep(1)
            timeout += 1
            if timeout % 5 == 0:
                _wdt_feed()
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
                log(f"IP: {ip} GW:{ifconfig[2]}")
                _check_ip_range(ip)
                _start_webrepl(ip)
                return True
        status = wlan.status()
        status_name = status_map.get(status, f'UNKNOWN({status})')
        log(f"✗ Intento #{attempt} falló - {status_name}")
        if attempt < max_attempts:
            if (status in [202, 201, 200] and attempt % 3 == 0) or (wlan.isconnected() and attempt > 1):
                log("🔄 Reset WiFi...")
                wlan = _reset_wlan()
                time.sleep(1)
            _wdt_feed()
            time.sleep(5)
    log("⚠ No se pudo conectar (3 intentos)")
    log("📡 Activando hotspot...")
    _start_ap_fallback(cfg)
    return False

def monitor_wifi(check_interval=30):
    import time
    import network
    log(f"=== Monitor WiFi ({check_interval}s) ===")
    wlan = _get_wlan()
    last_ip = None
    disconnected_count = 0
    while True:
        try:
            _wdt_feed()
            if wlan.isconnected():
                ifconfig = wlan.ifconfig()
                current_ip = ifconfig[0]
                if current_ip and current_ip != '0.0.0.0':
                    if last_ip != current_ip:
                        log(f"✓ WiFi: {current_ip} GW:{ifconfig[2]}")
                        last_ip = current_ip
                    disconnected_count = 0
                else:
                    disconnected_count += 1
                    if disconnected_count >= 3:
                        log("⚠ IP inválida, reset...")
                        wlan = _reset_wlan()
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
                    log("🔄 Reset WiFi...")
                    wlan = _reset_wlan()
                    time.sleep(2)
                    if _cfg:
                        connect_wifi(_cfg, _wdt_callback)
            time.sleep(check_interval)
        except Exception as e:
            log(f"⚠ Error monitoreo: {e}")
            time.sleep(check_interval)
