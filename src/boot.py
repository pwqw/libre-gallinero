# boot.py - Minimal bootstrap (MicroPython best practices)
# Only essential system initialization

import sys

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[boot] {msg}")
    # En MicroPython, sys.stdout puede ser uio.FileIO sin flush()
    if hasattr(sys.stdout, 'flush'):
        sys.stdout.flush()

log("=== Iniciando boot.py ===")

# Estado: Inicializando GC
try:
    import gc
    gc.collect()
    log("GC inicializado")
except Exception as e:
    log(f"Error en GC: {e}")

# Estado: Iniciando WebREPL
try:
    import webrepl
    webrepl.start()
    log("WebREPL iniciado en puerto 8266")
except Exception as e:
    log(f"Error iniciando WebREPL: {e}")

log("=== boot.py completado ===")
log("Listo para ejecutar main.py")

# Ejecutar main.py después de un delay para asegurar que WebREPL esté listo
# El delay permite que WebREPL se inicie completamente antes de comenzar WiFi
import time
log("Esperando 2 segundos para que WebREPL se inicie completamente...")
time.sleep(2)

try:
    import gc
    gc.collect()
    log("Memoria antes de importar main: {} bytes".format(gc.mem_free()))
    
    log("Importando main.py...")
    import main
    gc.collect()
    log("Memoria después de importar main: {} bytes".format(gc.mem_free()))
    
    log("Iniciando main.main() automáticamente...")
    main.main()
except MemoryError as e:
    log("ERROR: Memoria insuficiente para ejecutar main.py")
    log("El sistema seguirá funcionando con WebREPL disponible")
    log("Puedes ejecutar manualmente vía WebREPL: import main; main.main()")
except Exception as e:
    log("Error ejecutando main.py: {}".format(e))
    import sys
    sys.print_exception(e)
    log("El sistema seguirá funcionando, pero WiFi no se conectará automáticamente")
    log("Puedes ejecutar manualmente: import main; main.main()")
