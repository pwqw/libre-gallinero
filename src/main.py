# main.py - Main orchestrator
_wdt = None

def log(msg):
    print(f"[main] {msg}")
    try:
        import sys
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def feed_wdt():
    global _wdt
    if _wdt:
        try:
            _wdt.feed()
        except:
            pass

def main():
    global _wdt
    import gc
    
    # WDT - solo si está disponible
    try:
        from machine import WDT
        _wdt = WDT(60000)
        log("✅ WDT activado (60s)")
    except:
        _wdt = None
    
    gc.collect()
    log("=== Iniciando main.py ===")
    log(f"Memoria libre: {gc.mem_free()} bytes")
    
    # Cargar configuración
    import config
    cfg = config.load_config()
    app_name = cfg.get('APP', 'blink')
    log(f"App: {app_name}")
    gc.collect()
    
    # Conectar WiFi
    log("Conectando WiFi...")
    feed_wdt()
    import wifi
    wifi.connect_wifi(cfg, wdt_callback=feed_wdt)
    # Logging de memoria después de WiFi
    mem_after_wifi = gc.mem_free()
    log(f"Memoria libre (después de WiFi): {mem_after_wifi} bytes")
    
    # Monitoreo WiFi en background (opcional - solo si _thread disponible)
    try:
        import _thread
        _thread.start_new_thread(wifi.monitor_wifi, (30,))
        log("✅ Monitoreo WiFi iniciado")
    except ImportError:
        # _thread no disponible en este firmware - sistema funciona sin él
        pass
    except:
        # Otro error - ignorar silenciosamente
        pass
    
    # NTP
    feed_wdt()
    import ntp
    ntp_ok = ntp.sync_ntp()
    if not ntp_ok:
        log("⚠ NTP falló")
    feed_wdt()
    gc.collect()
    
    # Verificar estado WiFi después de conexión
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        wifi_connected = wlan.isconnected()
        wifi_ip = wlan.ifconfig()[0] if wifi_connected else None
    except:
        wifi_connected = False
        wifi_ip = None
    
    # Logging de memoria antes de cargar app
    mem_after_ntp = gc.mem_free()
    log(f"Memoria libre (después de NTP): {mem_after_ntp} bytes")
    
    # Mensaje de sistema listo
    log("=" * 40)
    log("✅ SISTEMA LISTO")
    log(f"  WiFi: {'✓' if wifi_connected else '✗'} {wifi_ip if wifi_ip else 'No conectado'}")
    log(f"  WebREPL: {'✓' if wifi_connected else '✗'}")
    log(f"  NTP: {'✓' if ntp_ok else '✗'}")
    log(f"  Memoria: {mem_after_ntp} bytes")
    log(f"  App: {app_name}")
    log("=" * 40)
    
    # Cargar app
    log("Cargando app...")
    feed_wdt()
    try:
        import app_loader
        app_loader.load_app(app_name, cfg)
        log("✅ App cargada")
    except ImportError:
        log("⚠ App no encontrada (normal en setup inicial)")
    except Exception as e:
        log(f"⚠ Error app: {e}")
    feed_wdt()
    
    log("✅ Sistema operativo")

if __name__ == '__main__' or True:
    try:
        main()
    except Exception as e:
        log(f"❌ Error fatal: {e}")
        import sys
        sys.print_exception(e)
