# main.py - Main orchestrator (minimal)
# Imports and calls other modules only when needed
# Este archivo se ejecuta automáticamente después de boot.py

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[main] {msg}")
    try:
        import sys
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

# Watchdog Timer global (inicializado en main())
_wdt = None

def feed_wdt():
    """Alimenta el watchdog timer para evitar reinicios"""
    global _wdt
    if _wdt:
        try:
            _wdt.feed()
        except:
            pass

def main():
    """Función principal - Se ejecuta automáticamente cuando MicroPython carga main.py"""
    global _wdt
    
    # Inicializar WDT si está disponible (heredado de boot.py o nuevo)
    try:
        from machine import WDT
        # Extender timeout a 60 segundos para operaciones de WiFi/NTP
        _wdt = WDT(timeout=60000)  # 60 segundos
        log("✅ Watchdog Timer activado (60s timeout)")
    except Exception as e:
        log(f"⚠ WDT no disponible: {e}")
    try:
        import gc
        gc.collect()
    except:
        pass
    
    log("=== Iniciando main.py ===")
    
    try:
        import network
        log("Módulo network importado")
    except ImportError as e:
        log(f"ERROR: network no encontrado: {e}")
        return

    try:
        import ntptime
        log("Módulo ntptime importado")
    except ImportError as e:
        log(f"ERROR: ntptime no encontrado: {e}")

    try:
        import machine
        log("Módulo machine importado")
    except ImportError as e:
        log(f"ERROR: machine no encontrado: {e}")

    try:
        gc.collect()
        log("GC inicializado y limpiado")
    except ImportError as e:
        log(f"ERROR: gc no encontrado: {e}")
    
    log("")
    log("=" * 50)
    log("Iniciando función main()")
    log("=" * 50)
    
    gc.collect()
    log(f"Memoria libre inicial: {gc.mem_free()} bytes")
    
    # Importar módulos solo cuando se necesiten (lazy loading)
    import config
    cfg = config.load_config()
    project = cfg.get('PROJECT', 'heladera')
    log(f"Configuración cargada")
    log(f"  SSID: {cfg.get('WIFI_SSID', 'N/A')}")
    log(f"  Proyecto: {project}")
    log(f"  Latitud: {cfg.get('LATITUDE', 'N/A')}")
    log(f"  Longitud: {cfg.get('LONGITUDE', 'N/A')}")
    gc.collect()
    log(f"Memoria libre después de cargar config: {gc.mem_free()} bytes")

    # Conectar WiFi (conecta inicialmente, luego monitorea en background)
    log("Iniciando conexión WiFi...")
    feed_wdt()  # Alimentar WDT antes de operación larga
    import wifi
    wifi.connect_wifi(cfg, wdt_callback=feed_wdt)  # Conexión inicial
    
    # Iniciar monitoreo WiFi en background (reconexión automática)
    # Esto corre en un loop infinito, pero no bloquea el resto del código
    # porque los proyectos (gallinero/heladera) se cargan después
    log("Iniciando monitoreo WiFi (reconexión automática)...")
    try:
        import _thread
        _thread.start_new_thread(wifi.monitor_wifi, (30,))  # Verificar cada 30s
        log("✅ Monitoreo WiFi iniciado en background")
    except:
        # Si _thread no está disponible, monitorear en el thread principal
        # (esto bloqueará, pero es mejor que nada)
        log("⚠ _thread no disponible, monitoreo en thread principal")
        # No llamamos monitor_wifi aquí porque bloquearía
        # En su lugar, el proyecto puede llamarlo si lo necesita

    # Sincronizar NTP
    feed_wdt()  # Alimentar WDT antes de operación de red
    import ntp
    ntp_synced = ntp.sync_ntp()
    if not ntp_synced:
        log("⚠ Sin NTP, reloj puede estar desincronizado")
    feed_wdt()  # Alimentar WDT después de NTP
    gc.collect()
    log(f"Memoria libre después de WiFi/NTP: {gc.mem_free()} bytes")

    # Cargar proyecto (opcional)
    log("")
    log("=" * 50)
    log("Iniciando carga de proyecto (opcional)")
    log("=" * 50)
    feed_wdt()  # Alimentar WDT antes de cargar proyecto
    try:
        import project_loader
        project_loader.load_project(project, cfg)
        log("✅ Proyecto cargado exitosamente")
        feed_wdt()  # Alimentar WDT después de cargar proyecto
    except Exception as e:
        log(f"⚠ No se pudo cargar el proyecto: {e}")
        log("Sistema funcionando en modo básico (WiFi + WebREPL disponible)")
        log("Puedes cargar el proyecto más tarde vía WebREPL o deploy")
        feed_wdt()  # Alimentar WDT incluso si falla
    
    log("✅ main.py completado - Sistema operativo")
    feed_wdt()  # Alimentar WDT final

# Ejecutar main() automáticamente cuando MicroPython carga este archivo
# Esto es lo que MicroPython hace después de ejecutar boot.py
if __name__ == '__main__' or True:  # Siempre ejecutar en MicroPython
    try:
        main()
    except KeyboardInterrupt:
        log("⚠ Interrupción por teclado")
    except Exception as e:
        log(f"❌ Error fatal en main(): {e}")
        import sys
        sys.print_exception(e)
        log("⚠ Sistema en modo seguro - WebREPL disponible para diagnóstico")
