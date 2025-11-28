# Blink App - LED blink example
# App minimalista para setup inicial y testing básico
# Interfaz común: run(cfg)

try:
    import machine
    import time
    import gc
except ImportError:
    print("[blink] ERROR: Módulos MicroPython no encontrados")

# LED pin (built-in LED on NodeMCU is usually GPIO 2)
LED_PIN = 2

def run(cfg):
    """
    Función principal de la app blink.
    
    App minimalista para setup inicial y testing básico.
    Interfaz común para todas las apps: recibe cfg y ejecuta el loop principal.
    """
    print('\n=== blink/app ===')
    gc.collect()
    
    try:
        # Obtener configuración (opcional)
        pin = int(cfg.get('LED_PIN', LED_PIN))
        delay = float(cfg.get('LED_DELAY', 0.66))
        
        led = machine.Pin(pin, machine.Pin.OUT)
        print(f'[blink] LED inicializado en pin {pin}')
        gc.collect()
        
        print('[blink] Loop principal...')
        
        # Contador para heartbeat periódico
        iteration = 0
        # Heartbeat cada ~60 segundos (ajustar según delay)
        # Con delay=0.5, cada 120 iteraciones = 60 segundos
        heartbeat_interval = max(60, int(60 / delay)) if delay > 0 else 120
        
        while True:
            led.on()
            time.sleep(delay)
            led.off()
            time.sleep(delay)
            gc.collect()
            
            iteration += 1
            
            # Heartbeat periódico para mantener serial activo
            if iteration % heartbeat_interval == 0:
                try:
                    tm = time.localtime()
                    mem = gc.mem_free()
                    timestamp = f"{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}"
                    print(f'[blink] 💓 {timestamp} | Mem: {mem}B | Iter: {iteration}')
                    # Flush para asegurar salida inmediata
                    import sys
                    if hasattr(sys.stdout, 'flush'):
                        sys.stdout.flush()
                except:
                    pass
    except Exception as e:
        print(f'[blink] Error: {e}')
        import sys
        sys.print_exception(e)

