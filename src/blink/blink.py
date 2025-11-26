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
        delay = float(cfg.get('LED_DELAY', 0.5))
        
        led = machine.Pin(pin, machine.Pin.OUT)
        print(f'[blink] LED inicializado en pin {pin}')
        gc.collect()
        
        print('[blink] Loop principal...')
        while True:
            led.on()
            time.sleep(delay)
            led.off()
            time.sleep(delay)
            gc.collect()
    except Exception as e:
        print(f'[blink] Error: {e}')
        import sys
        sys.print_exception(e)

