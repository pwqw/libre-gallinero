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

    # Cargar app como generador (patrón cooperativo)
    log("Modo: cooperativo")
    app_gen=None
    try:
        import app_loader
        app_gen=app_loader.load_app(app_name,cfg)
        if app_gen is None:
            log("⚠ App no retorna generador")
        else:
            log("App lista")
    except ImportError:
        log("⚠ App no encontrada")
    except Exception as e:
        log(f"⚠ Error app:{e}")
        import sys
        sys.print_exception(e)

    feed_wdt()
    gc.collect()
    log("="*40)
    log("LOOP PRINCIPAL")
    log(f"Mem:{gc.mem_free()}")
    log("="*40)

    # Loop principal cooperativo (NO bloquea WebREPL)
    import time
    tick_count=0
    app_delay=0.5  # Delay base entre ticks

    while True:
        feed_wdt()

        # Ejecutar 1 tick de app (si existe)
        if app_gen:
            try:
                # Timeout implícito: si app no hace yield rápido, bloqueará
                # pero al menos main.py tiene sleep() que libera WebREPL
                next(app_gen)
            except StopIteration:
                log("⚠ App terminó")
                app_gen=None
            except Exception as e:
                log(f"⚠ App error:{e}")
                app_gen=None

        # Sleep para liberar WebREPL
        time.sleep(app_delay)

        # Heartbeat periódico (cada ~60s)
        tick_count+=1
        if tick_count%(int(60/app_delay))==0:
            gc.collect()
            tm=time.localtime()
            log(f"💓 {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d} | Mem:{gc.mem_free()}")

if __name__=='__main__':
    try:main()
    except Exception as e:
        log(f"❌ Error fatal:{e}")
        import sys;sys.print_exception(e)
