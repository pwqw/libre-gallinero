# boot.py - Minimal bootstrap (solo protección esencial)
# MicroPython ejecutará main.py automáticamente después

# Watchdog Timer: protege contra bloqueos (reinicia si > 30s sin respuesta)
try:
    from machine import WDT
    wdt = WDT(timeout=30000)
except:
    wdt = None

# Limpieza inicial de memoria
try:
    import gc
    gc.collect()
except:
    pass

# Listo. MicroPython ejecutará main.py ahora.
