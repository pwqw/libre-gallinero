# Heladera App - LED blink example
# Interfaz común: run(cfg)
import sys

try:
    import machine
    import time
    import gc
except ImportError:
    print("[heladera/blink] ERROR: Módulos MicroPython no encontrados")

# LED pin (built-in LED on NodeMCU is usually GPIO 2)
LED_PIN = 2

def run(cfg):
    """
    Función principal de la app heladera.
    
    Interfaz común para todas las apps: recibe cfg y ejecuta el loop principal.
    """
    print('\n=== heladera/app ===')
    gc.collect()
    
    try:
        # Obtener configuración (opcional)
        pin = int(cfg.get('LED_PIN', LED_PIN))
        delay = float(cfg.get('LED_DELAY', 0.24))
        
        led = machine.Pin(pin, machine.Pin.OUT)
        print(f'[heladera] LED inicializado en pin {pin}')
        gc.collect()
        
        print('[heladera] Loop principal...')
        while True:
            led.on()
            time.sleep(delay)
            led.off()
            time.sleep(delay)
            gc.collect()
    except Exception as e:
        print(f'[heladera] Error: {e}')
        sys.print_exception(e)

