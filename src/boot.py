# boot.py - Bootstrap: WDT + WiFi + WebREPL + Hotspot de Emergencia
# CRÍTICO: Si WiFi falla, crea hotspot 192.168.4.1 para recuperación
# Patrón oficial MicroPython: WiFi primero, luego WebREPL
# Docs: https://docs.micropython.org/en/latest/esp8266/tutorial/network_basics.html

import gc
gc.collect()

# WDT: protege contra bloqueos
try:
    from machine import WDT
    wdt = WDT(30000)
except:
    wdt = None

def do_connect():
    """Conecta WiFi (patrón oficial docs.micropython.org)"""
    import network
    import time
    import config

    cfg = config.load_config()
    ssid = cfg.get('WIFI_SSID', '').strip()
    pwd = cfg.get('WIFI_PASSWORD', '').strip()

    if not ssid:
        print('[boot] Sin WiFi config')
        return False, cfg

    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)

    if sta_if.isconnected():
        print(f'[boot] WiFi OK: {sta_if.ifconfig()[0]}')
        return True, cfg

    print(f'[boot] Conectando WiFi...')
    sta_if.connect(ssid, pwd)

    timeout = 15
    while not sta_if.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1

    if sta_if.isconnected():
        print(f'[boot] WiFi OK: {sta_if.ifconfig()[0]}')
        return True, cfg
    else:
        print('[boot] WiFi timeout')
        return False, cfg

def create_emergency_hotspot(cfg):
    """Crea hotspot de emergencia si WiFi falla - SIEMPRE ACCESIBLE"""
    import network
    import time
    
    print('[boot] ========================================')
    print('[boot] MODO EMERGENCIA: Creando Hotspot')
    print('[boot] ========================================')
    
    try:
        # Desactivar station mode
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(False)
        time.sleep(0.5)
        
        # Activar AP mode
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        
        # Configurar hotspot
        ap_pwd = cfg.get('WIFI_PASSWORD', 'libre123')
        if not ap_pwd or ap_pwd.strip() == '':
            ap_pwd = 'libre123'
        
        ap.config(essid='ESP8266-RECOVERY', password=ap_pwd)
        ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
        
        print('[boot] ========================================')
        print('[boot] HOTSPOT ACTIVO:')
        print('[boot]   SSID: ESP8266-RECOVERY')
        print('[boot]   IP:   192.168.4.1:8266')
        print('[boot]   Pass: ' + ap_pwd)
        print('[boot] ========================================')
        print('[boot] Conectate y usa: ws://192.168.4.1:8266')
        print('[boot] ========================================')
        
        return True
    except Exception as e:
        print(f'[boot] ERROR Hotspot: {e}')
        return False

# Conectar WiFi
wifi_ok, cfg = do_connect()

# Si WiFi falla, crear hotspot de emergencia
if not wifi_ok:
    print('[boot] WiFi FALLO - Activando modo emergencia')
    hotspot_ok = create_emergency_hotspot(cfg)
    if not hotspot_ok:
        print('[boot] ERROR CRÍTICO: No se pudo crear hotspot')
        print('[boot] Dispositivo INACCESIBLE - Requiere USB')

# WebREPL: SIEMPRE intentar iniciar (funciona en WiFi Y en hotspot)
try:
    import webrepl, time
    webrepl.start()
    time.sleep(0.1)
    print('[boot] WebREPL OK')
except Exception as e:
    print(f'[boot] WebREPL error: {e}')
    print('[boot] Verifica: webrepl_setup configurado')

gc.collect()
# Listo. MicroPython ejecutará main.py ahora.
