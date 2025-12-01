# Heladera App - Modo Debug Simple
import sys
try:
    import machine
    import time
    import gc
    import logger
except ImportError:
    print("[heladera/app] ERROR: Módulos MicroPython no encontrados")

RELAY_PIN = 5
LED_PIN = 2
CYCLE_DURATION = 60  # 1 minuto para debugging

def run(cfg):
    """Generador cooperativo - yield cada tick (~100ms desde main.py)"""
    logger.log('heladera', '=== Heladera App (Debug Mode) ===')
    gc.collect()
    
    try:
        # Inicializar hardware
        relay = machine.Pin(RELAY_PIN, machine.Pin.OUT)
        led = machine.Pin(LED_PIN, machine.Pin.OUT)
        logger.log('heladera', f'Hardware OK - RELE pin {RELAY_PIN}, LED pin {LED_PIN}')
        
        # Estado inicial: RELE ON, LED OFF
        relay.on()
        led.off()
        state_relay_on = True
        logger.log('heladera', 'Estado inicial: RELE ON, LED OFF')
        
        cycle_start = time.time()
        tick_count = 0
        
        # Loop cooperativo principal
        while True:
            current_time = time.time()
            elapsed = current_time - cycle_start
            tick_count += 1
            
            # Cada 1 minuto, alternar estado
            if elapsed >= CYCLE_DURATION:
                state_relay_on = not state_relay_on
                
                if state_relay_on:
                    # RELE ON, LED OFF
                    relay.on()
                    led.off()
                    logger.log('heladera', 'CAMBIO: RELE ON, LED OFF')
                else:
                    # RELE OFF, LED ON
                    relay.off()
                    led.on()
                    logger.log('heladera', 'CAMBIO: RELE OFF, LED ON')
                
                cycle_start = current_time
                logger.log('heladera', f'Ciclo reiniciado (tick #{tick_count})')
                gc.collect()
            
            # Log cada 10 segundos para debugging
            if tick_count % 100 == 0:  # 100 ticks × 100ms = 10s
                remaining = CYCLE_DURATION - elapsed
                logger.log('heladera', f'Estado: RELE {"ON" if state_relay_on else "OFF"}, LED {"OFF" if state_relay_on else "ON"} - {remaining:.1f}s restantes')
            
            yield  # Liberar control a main.py
            
    except KeyboardInterrupt:
        logger.log('heladera', 'Interrumpido por usuario')
        try:
            relay.off()
            led.off()
            logger.log('heladera', 'Hardware apagado')
        except:
            pass
    except Exception as e:
        logger.log('heladera', f'ERROR: {e}')
        try:
            sys.print_exception(e)
        except:
            pass
