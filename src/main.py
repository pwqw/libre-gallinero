# main.py - Main orchestrator
_wdt=None
_logger=None
def log(msg):
 if _logger:_logger.log('main',msg)
 else:print(f"[main] {msg}")
def feed_wdt():
    global _wdt
    if _wdt:
        try:_wdt.feed()
        except:pass
def main():
    global _wdt,_logger
    import gc
    import logger
    _logger=logger
    logger.init(100)
    try:
        from machine import WDT
        _wdt=WDT(60000)
        log("WDT 60s")
    except:_wdt=None
    gc.collect()
    log("=== Iniciando ===")
    log(f"Mem: {gc.mem_free()} bytes")
    
    import config
    cfg=config.load_config()
    app_name=cfg.get('APP','blink')
    log(f"App: {app_name}")
    gc.collect()
    log("Conectando WiFi...")
    feed_wdt()
    import wifi
    wifi.connect_wifi(cfg,wdt_callback=feed_wdt)
    log(f"Mem(post-WiFi): {gc.mem_free()}")
    try:
        import _thread
        _thread.start_new_thread(wifi.monitor_wifi,(30,))
        log("Monitor WiFi OK")
    except:pass
    feed_wdt()
    import ntp
    longitude=cfg.get('LONGITUDE',-64.1833)
    ntp_ok=ntp.sync_ntp(longitude=longitude)
    if not ntp_ok:log("⚠ NTP falló")
    feed_wdt()
    gc.collect()
    try:
        import network
        wlan=network.WLAN(network.STA_IF)
        wifi_ok=wlan.isconnected()
        wifi_ip=wlan.ifconfig()[0]if wifi_ok else None
    except:
        wifi_ok=False
        wifi_ip=None
    mem=gc.mem_free()
    log("="*40)
    log("SISTEMA LISTO")
    log(f"WiFi:{'✓'if wifi_ok else'✗'} {wifi_ip if wifi_ip else'No'}")
    log(f"WebREPL:{'✓'if wifi_ok else'✗'}")
    log(f"NTP:{'✓'if ntp_ok else'✗'}")
    log(f"Mem:{mem}")
    log(f"App:{app_name}")
    log("="*40)
    log("Cargando app...")
    feed_wdt()
    try:
        import app_loader
        app_loader.load_app(app_name,cfg)
        log("App cargada")
    except ImportError:
        log("⚠ App no encontrada")
    except Exception as e:
        log(f"⚠ Error app:{e}")
    feed_wdt()
    log("Sistema operativo")

if __name__ == '__main__' or True:
    try:
        main()
    except Exception as e:
        log(f"❌ Error fatal: {e}")
        import sys
        sys.print_exception(e)
