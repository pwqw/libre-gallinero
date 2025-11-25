# main.py - Main orchestrator (minimal)
# Imports and calls other modules only when needed

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[main] {msg}")
    try:
        import sys
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def main():
    """Función principal - Se ejecuta automáticamente desde boot.py"""
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
    project = cfg.get('PROJECT', 'gallinero')
    log(f"Configuración cargada")
    log(f"  SSID: {cfg.get('WIFI_SSID', 'N/A')}")
    log(f"  Proyecto: {project}")
    log(f"  Latitud: {cfg.get('LATITUDE', 'N/A')}")
    log(f"  Longitud: {cfg.get('LONGITUDE', 'N/A')}")
    gc.collect()
    log(f"Memoria libre después de cargar config: {gc.mem_free()} bytes")

    # Conectar WiFi
    log("Iniciando conexión WiFi (reintentos infinitos)...")
    import wifi
    wifi.connect_wifi(cfg)

    # Sincronizar NTP
    import ntp
    ntp_synced = ntp.sync_ntp()
    if not ntp_synced:
        log("⚠ Sin NTP, reloj puede estar desincronizado")
    gc.collect()
    log(f"Memoria libre después de WiFi/NTP: {gc.mem_free()} bytes")

    # Cargar proyecto (opcional)
    log("")
    log("=" * 50)
    log("Iniciando carga de proyecto (opcional)")
    log("=" * 50)
    try:
        import project_loader
        project_loader.load_project(project, cfg)
        log("✅ Proyecto cargado exitosamente")
    except Exception as e:
        log(f"⚠ No se pudo cargar el proyecto: {e}")
        log("Sistema funcionando en modo básico (WiFi + WebREPL disponible)")
        log("Puedes cargar el proyecto más tarde vía WebREPL o deploy")
