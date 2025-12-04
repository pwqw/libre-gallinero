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
    import time
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
    tz_offset=cfg.get('TIMEZONE','-3')
    if isinstance(tz_offset,str):
        tz_offset=int(tz_offset)
    ntp_ok,ntp_timestamp=ntp.sync_ntp(tz_offset=tz_offset)
    if not ntp_ok:log("⚠ NTP falló")
    else:log(f"NTP sync OK")
    
    # Configurar intervalo de resync NTP
    ntp_resync_interval=3600  # default 1 hora
    try:
        ntp_resync_str=cfg.get('NTP_RESYNC_INTERVAL_SECONDS','3600')
        ntp_resync_interval=int(ntp_resync_str)
    except:pass
    last_ntp_sync_time=ntp_timestamp if ntp_ok else 0
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
    tick_count=0
    webrepl_delay=0.01  # 10ms: libera WebREPL frecuentemente
    app_tick_interval=10  # Ejecutar app cada 10 loops (100ms)
    ntp_resync_check_interval=3600  # Verificar resync cada hora (3600 ticks × 10ms = 36s, pero check cada 360000 ticks = 1h)

    while True:
        feed_wdt()

        # Ejecutar app cada N loops (controla velocidad app)
        if tick_count%app_tick_interval==0 and app_gen:
            try:
                next(app_gen)
            except StopIteration:
                log("⚠ App terminó")
                app_gen=None
            except Exception as e:
                log(f"⚠ App error:{e}")
                app_gen=None

        # Verificar resync NTP periódicamente (cada hora)
        if tick_count%360000==0 and tick_count>0:  # 360000 ticks × 10ms = 3600s = 1h
            current_time=time.time()
            # Verificar si necesitamos resync
            if last_ntp_sync_time==0 or (current_time-last_ntp_sync_time)>=ntp_resync_interval:
                log(f"Resync NTP (último: {last_ntp_sync_time}, intervalo: {ntp_resync_interval}s)")
                feed_wdt()
                try:
                    import network
                    wlan=network.WLAN(network.STA_IF)
                    if wlan.isconnected():
                        ntp_ok,ntp_timestamp=ntp.sync_ntp(tz_offset=tz_offset)
                        if ntp_ok:
                            last_ntp_sync_time=ntp_timestamp
                            log(f"✓ NTP resync OK: {ntp_timestamp}")
                        else:
                            log("✗ NTP resync falló")
                    else:
                        log("⚠ WiFi desconectado, skip NTP resync")
                except Exception as e:
                    log(f"⚠ Error NTP resync: {e}")
                feed_wdt()
                gc.collect()

        # Sleep corto → WebREPL responde rápido
        time.sleep(webrepl_delay)

        tick_count+=1
        # Heartbeat cada ~15s (1500 ticks × 10ms) - más frecuente para WebREPL
        if tick_count%1500==0:
            gc.collect()
            tm=time.localtime()
            # Formatear hora si hay NTP (año > 2000 indica hora válida)
            if tm[0]>2000:
                hora_str=f"{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}"
            else:
                hora_str="--:--:--"
            log(f"💓 {hora_str} | Mem:{gc.mem_free()}B | App:{app_name} running")

if __name__=='__main__':
    try:main()
    except Exception as e:
        log(f"❌ Error fatal:{e}")
        import sys;sys.print_exception(e)
