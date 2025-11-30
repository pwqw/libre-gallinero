# Blink App - LED blink example
# App minimalista para setup inicial y testing básico
# Patrón cooperativo: generador que hace yield en cada tick
import sys

try:
    import machine
    import gc
except ImportError:
    print("[blink] ERROR: Módulos MicroPython no encontrados")

# LED pin (built-in LED on NodeMCU is usually GPIO 2)
LED_PIN = 2

def run(cfg):
    """
    Generador cooperativo para blink app.

    Retorna generador que ejecuta 1 tick por next():
    - Toggle LED
    - yield (cede control a main.py)

    NO usa while True ni sleep() → main.py controla timing.
    """
    print('\n=== blink/app ===')
    gc.collect()

    try:
        # Setup
        pin = int(cfg.get('LED_PIN', LED_PIN))
        led = machine.Pin(pin, machine.Pin.OUT)
        print(f'[blink] LED pin {pin} | Modo cooperativo')
        gc.collect()

        # Loop generador (yield en cada tick)
        state = False
        iteration = 0

        while True:
            # Toggle LED
            state = not state
            led.value(state)

            iteration += 1

            # Heartbeat periódico (cada ~120 ticks ≈ 60s con delay 0.5s)
            if iteration % 120 == 0:
                try:
                    import time
                    tm = time.localtime()
                    mem = gc.mem_free()
                    print(f'[blink] 💓 {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d} | Mem:{mem} | #{iteration}')
                    if hasattr(sys.stdout, 'flush'):
                        sys.stdout.flush()
                    gc.collect()
                except:
                    pass

            # Ceder control a main.py (CRÍTICO para WebREPL)
            yield

    except Exception as e:
        print(f'[blink] Error: {e}')
        sys.print_exception(e)

