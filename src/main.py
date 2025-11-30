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

    # WiFi ya conectado en boot.py (patrón oficial MicroPython)
    # Solo verificamos estado
    try:
        import network
        wlan=network.WLAN(network.STA_IF)
        if wlan.isconnected():
            log(f"WiFi: {wlan.ifconfig()[0]}")
        else:
            log("⚠ WiFi no conectado (revisar boot.py)")
    except:pass

    feed_wdt()
    import ntp
    longitude=cfg.get('LONGITUDE',-64.1833)
    # Convert to float if string (from .env config)
    if isinstance(longitude, str):
        longitude=float(longitude)
    ntp_ok=ntp.sync_ntp(longitude=longitude)
    if not ntp_ok:log("⚠ NTP falló")
    feed_wdt()
    gc.collect()

    # Detectar soporte threading
    thread_ok=False
    try:
        import _thread
        thread_ok=True
        log("Thread: ✓")
    except:
        log("Thread: ✗")

    log("="*40)
    log("SISTEMA LISTO")
    log(f"NTP:{'✓'if ntp_ok else'✗'}")
    log(f"Mem:{gc.mem_free()}")
    log(f"App:{app_name}")
    log("="*40)
    log("Cargando app...")
    feed_wdt()

    if thread_ok:
        # Ejecutar app en thread separado → libera main thread para WebREPL
        log("Modo: thread")
        try:
            import app_loader
            def run_app():
                try:
                    app_loader.load_app(app_name,cfg)
                except Exception as e:
                    log(f"⚠ App thread:{e}")
            _thread.start_new_thread(run_app,())
            log("App en background")
        except Exception as e:
            log(f"⚠ Thread error:{e}")
    else:
        # Sin threading → app bloquea (WebREPL no funcionará)
        log("Modo: blocking")
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
