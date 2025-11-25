# boot.py - Minimal bootstrap (MicroPython best practices)
# Only essential system initialization

import sys

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[boot] {msg}")
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
