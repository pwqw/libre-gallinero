# wifi.py - WiFi connection manager
import logger
_wlan=None
_cfg=None
_wdt_callback=None
_webrepl_active=False
_webrepl_ip=None
_was_connected_before=False
def log(msg):
 logger.log('wifi',msg)

def _get_wlan():
    global _wlan
    if _wlan is None:
        import network
        _wlan=network.WLAN(network.STA_IF)
        _wlan.active(True)
    return _wlan
def _reset_wlan():
    global _wlan
    import network,time
    if _wlan is not None:
        try:
            if _wlan.isconnected():_wlan.disconnect()
            _wlan.active(False)
            time.sleep(0.5)
        except:pass
    _wlan=network.WLAN(network.STA_IF)
    _wlan.active(True)
    time.sleep(0.5)
    return _wlan

def _start_ap_fallback(cfg):
    try:
        import network
        ap=network.WLAN(network.AP_IF)
        ap_pw=cfg.get('WIFI_PASSWORD','1234')
        if not ap_pw or ap_pw.strip()=='':ap_pw='1234'
        if isinstance(ap_pw,bytes):ap_pw=ap_pw.decode('utf-8')
        ap.active(True)
        ap.config(essid='Gallinero-Setup',password=ap_pw)
        ap.ifconfig(('192.168.4.1','255.255.255.0','192.168.4.1','192.168.4.1'))
        log("📡 Hotspot: Gallinero-Setup")
        log("   IP: 192.168.4.1")
        _start_webrepl('192.168.4.1')
        return True
    except Exception as e:
        log(f"✗ AP: {e}")
        return False
def _start_webrepl(ip, force_restart=False):
    """Inicia/reinicia WebREPL solo si es necesario"""
    global _webrepl_active, _webrepl_ip
    if _webrepl_active and _webrepl_ip == ip and not force_restart:
        log(f"WebREPL ya activo en {ip}")
        return True
    try:
        import webrepl, gc
        webrepl.start()
        _webrepl_active = True
        _webrepl_ip = ip
        log(f"✅ WebREPL: ws://{ip}:8266")
        gc.collect()
        log(f"Mem: {gc.mem_free()} bytes")
        return True
    except Exception as e:
        log(f"⚠ WebREPL error: {e}")
        _webrepl_active = False
        _webrepl_ip = None
        return False
def _check_ip_range(ip):
    if not ip.startswith('192.168.0.'):log("⚠ IP fuera rango")
def _wdt_feed():
    if _wdt_callback:
        try:_wdt_callback()
        except:pass
def _sync_ntp_on_reconnect():
    """Actualiza NTP automáticamente al reconectar WiFi (fallback silencioso)"""
    try:
        import ntp
        tz_offset=-3
        if _cfg:
            tz_str=_cfg.get('TIMEZONE','-3')
            try:tz_offset=int(tz_str)
            except:pass
        log("🕐 NTP auto-sync...")
        ntp_ok,ntp_timestamp=ntp.sync_ntp(tz_offset=tz_offset)
        if ntp_ok:
            log("✓ NTP auto-sync OK")
        else:
            log("⚠ NTP auto-sync falló (continuando)")
    except Exception as e:
        log(f"⚠ NTP auto-sync error: {e} (continuando)")

def connect_wifi(cfg,wdt_callback=None):
    global _cfg,_wdt_callback,_was_connected_before
    _cfg=cfg
    _wdt_callback=wdt_callback
    import network,time
    log("=== WiFi ===")
    wlan=_get_wlan()
    was_already_connected=wlan.isconnected()
    if was_already_connected:
        ifconfig=wlan.ifconfig()
        ip=ifconfig[0]
        if ip and ip!='0.0.0.0':
            log(f"WiFi SDK auto: {ip}")
            _check_ip_range(ip)
            _start_webrepl(ip)
            try:
                ap=network.WLAN(network.AP_IF)
                if ap.active():ap.active(False)
            except:pass
            if _was_connected_before:
                _sync_ntp_on_reconnect()
            _was_connected_before=True
            return True
    ssid=cfg.get('WIFI_SSID','').strip()
    pw=cfg.get('WIFI_PASSWORD','').strip()
    hidden=cfg.get('WIFI_HIDDEN','false').lower()=='true'
    if not ssid or ssid=='':
        log("⚠ No WiFi config")
        log("📡 Activando hotspot...")
        _start_ap_fallback(cfg)
        return False
    if isinstance(ssid,bytes):ssid=ssid.decode('utf-8')
    if isinstance(pw,bytes):pw=pw.decode('utf-8')
    log(f"Red: {repr(ssid)} (oculta: {hidden})")
    _wdt_feed()
    try:
        log("SDK cache...")
        wlan.connect()
        time.sleep(5)
        if wlan.isconnected():
            ifconfig=wlan.ifconfig()
            ip=ifconfig[0]
            if ip and ip!='0.0.0.0':
                log(f"✓✓ SDK cache OK: {ip}")
                _check_ip_range(ip)
                _start_webrepl(ip)
                if _was_connected_before:
                    _sync_ntp_on_reconnect()
                _was_connected_before=True
                return True
    except:pass
    max_attempts=3
    attempt=0
    status_map={1000:'IDLE',1001:'CONNECTING',1010:'GOT_IP',202:'WRONG_PASSWORD',201:'NO_AP_FOUND',200:'CONNECT_FAIL'}
    while attempt<max_attempts:
        attempt+=1
        log(f"Intento #{attempt}/{max_attempts}")
        _wdt_feed()
        if not hidden and(attempt==1 or attempt%5==0):
            try:
                networks=wlan.scan()
                found=any((net[0].decode('utf-8')if isinstance(net[0],bytes)else net[0])==ssid for net in networks)
                log(f"{'✓' if found else '⚠'} Red scan")
            except:pass
        if wlan.status()==network.STAT_CONNECTING:
            wlan.disconnect()
            time.sleep(1)
        if attempt>1 and attempt%3==0:
            log("Reset WiFi")
            wlan=_reset_wlan()
            time.sleep(1)
        log(f"Conectando {repr(ssid)}")
        try:
            wlan.connect(ssid,pw)
        except Exception as e:
            log(f"✗ {e}")
            time.sleep(5)
            continue
        timeout_s=30 if hidden else 15
        timeout=0
        while not wlan.isconnected()and timeout<timeout_s:
            time.sleep(1)
            timeout+=1
            if timeout%5==0:_wdt_feed()
            status=wlan.status()
            status_name=status_map.get(status,f'?({status})')
            if timeout%5==0:log(f"Wait {timeout}/{timeout_s}s {status_name}")
            if status in[202,201,200]:
                log(f"✗ {status_name}")
                break
        if wlan.isconnected():
            time.sleep(0.5)
            ifconfig=wlan.ifconfig()
            ip=ifconfig[0]
            if ip=='0.0.0.0'or not ip:
                time.sleep(2)
                ifconfig=wlan.ifconfig()
                ip=ifconfig[0]
            if ip and ip!='0.0.0.0':
                log("✓✓✓ WiFi OK ✓✓✓")
                log(f"IP:{ip} GW:{ifconfig[2]}")
                _check_ip_range(ip)
                _start_webrepl(ip)
                if _was_connected_before:
                    _sync_ntp_on_reconnect()
                _was_connected_before=True
                return True
        status=wlan.status()
        status_name=status_map.get(status,f'?({status})')
        log(f"✗ #{attempt} fail {status_name}")
        if attempt<max_attempts:
            if(status in[202,201,200]and attempt%3==0)or(wlan.isconnected()and attempt>1):
                log("Reset WiFi")
                wlan=_reset_wlan()
                time.sleep(1)
            _wdt_feed()
            time.sleep(5)
    log("⚠ No se pudo conectar (3 intentos)")
    log("📡 Activando hotspot...")
    _start_ap_fallback(cfg)
    return False

def monitor_wifi(check_interval=30):
    """Monitor WiFi con reinicio inteligente de WebREPL"""
    import time,network
    global _webrepl_active, _webrepl_ip,_was_connected_before
    log(f"Monitor WiFi ({check_interval}s)")
    wlan=_get_wlan()
    last_ip=None
    dc=0
    was_connected=False
    while True:
        try:
            _wdt_feed()
            if wlan.isconnected():
                ifconfig=wlan.ifconfig()
                ip=ifconfig[0]
                if ip and ip!='0.0.0.0':
                    if last_ip!=ip:
                        log(f"✓ WiFi:{ip} GW:{ifconfig[2]}")
                        force_restart = not was_connected or (last_ip is not None and last_ip != ip)
                        _start_webrepl(ip, force_restart=force_restart)
                        last_ip=ip
                        # Si se reconectó después de estar desconectado, actualizar NTP
                        if not was_connected and _was_connected_before:
                            _sync_ntp_on_reconnect()
                        was_connected=True
                        _was_connected_before=True
                    dc=0
                else:
                    dc+=1
                    if dc>=3:
                        log("⚠ IP inválida, reset")
                        _webrepl_active=False
                        _webrepl_ip=None
                        wlan=_reset_wlan()
                        time.sleep(2)
                        if _cfg:connect_wifi(_cfg,_wdt_callback)
            else:
                if was_connected:
                    log("⚠ WiFi desconectado")
                    _webrepl_active=False
                    _webrepl_ip=None
                    was_connected=False
                dc+=1
                if dc==1:log("⚠ WiFi desconectado")
                elif dc%5==0:log(f"⚠ WiFi desc ({dc} checks)")
                if dc>=2:
                    log("Reset WiFi")
                    wlan=_reset_wlan()
                    time.sleep(2)
                    if _cfg:connect_wifi(_cfg,_wdt_callback)
            time.sleep(check_interval)
        except Exception as e:
            log(f"⚠ Monitor: {e}")
            time.sleep(check_interval)
