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
    project = cfg.get('PROJECT', 'heladera')
    log(f"Proyecto: {project}")
    gc.collect()
    
    # Conectar WiFi
    log("Conectando WiFi...")
    feed_wdt()
    import wifi
    wifi.connect_wifi(cfg, wdt_callback=feed_wdt)
    
    # Monitoreo WiFi en background
    try:
        import _thread
        _thread.start_new_thread(wifi.monitor_wifi, (30,))
        log("✅ Monitoreo WiFi iniciado")
    except:
        log("⚠ _thread no disponible")
    
    # NTP
    feed_wdt()
    import ntp
    if not ntp.sync_ntp():
        log("⚠ NTP falló")
    feed_wdt()
    gc.collect()
    
    # Cargar proyecto (opcional)
    log("Cargando proyecto...")
    feed_wdt()
    try:
        import project_loader
        project_loader.load_project(project, cfg)
        log("✅ Proyecto cargado")
    except ImportError:
        log("⚠ Proyecto no encontrado (normal en setup inicial)")
    except Exception as e:
        log(f"⚠ Error proyecto: {e}")
    feed_wdt()
    
    log("✅ Sistema operativo")

if __name__ == '__main__' or True:
    try:
        main()
    except Exception as e:
        log(f"❌ Error fatal: {e}")
        import sys
        sys.print_exception(e)
