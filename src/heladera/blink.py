# Simple LED blink example for heladera project

try:
    import machine
    import time
    import gc
except ImportError:
    print("[heladera/blink] ERROR: Módulos MicroPython no encontrados")

# LED pin (built-in LED on NodeMCU is usually GPIO 2)
LED_PIN = 2

def blink_led(pin=LED_PIN, delay=0.5):
    """Simple LED blink function"""
    try:
        led = machine.Pin(pin, machine.Pin.OUT)
        print(f'[heladera/blink] LED inicializado en pin {pin}')
        gc.collect()
        
        while True:
            led.on()
            time.sleep(delay)
            led.off()
            time.sleep(delay)
            gc.collect()
    except Exception as e:
        print(f'[heladera/blink] Error: {e}')

