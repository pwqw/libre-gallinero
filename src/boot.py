# boot.py - Bootstrap: WDT + WiFi + WebREPL
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
        return False

    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)

    if sta_if.isconnected():
        print(f'[boot] WiFi OK: {sta_if.ifconfig()[0]}')
        return True

    print(f'[boot] Conectando WiFi...')
    sta_if.connect(ssid, pwd)

    timeout = 15
    while not sta_if.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1

    if sta_if.isconnected():
        print(f'[boot] WiFi OK: {sta_if.ifconfig()[0]}')
        return True
    else:
        print('[boot] WiFi timeout')
        return False

# Conectar WiFi
wifi_ok = do_connect()

# WebREPL: DESPUÉS de WiFi (según docs oficiales)
if wifi_ok:
    try:
        import webrepl
        webrepl.start()
        print('[boot] WebREPL OK')
    except:
        print('[boot] WebREPL error (run webrepl_setup)')

gc.collect()
# Listo. MicroPython ejecutará main.py ahora.
