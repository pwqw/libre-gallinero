# Heladera App - Modo Debug Simple
#
# IMPORTANTE: Hardware "Active Low"
# - LED pin 2 (NodeMCU built-in): Se enciende con LOW (0), se apaga con HIGH (1)
# - Relé módulo común: Se activa con LOW (0), se desactiva con HIGH (1)
# Esto es NORMAL en hardware embebido. El código invierte la lógica para que
# los logs representen el estado lógico (ON/OFF) en lugar del estado físico (HIGH/LOW).
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
        # Hardware "active low": LOW (off()) activa relé, HIGH (on()) apaga LED
        relay.off()  # LOW = relé activado (ON)
        led.on()     # HIGH = LED apagado (OFF)
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
                    # Hardware "active low": LOW activa relé, HIGH apaga LED
                    relay.off()  # LOW = relé activado (ON)
                    led.on()     # HIGH = LED apagado (OFF)
                    logger.log('heladera', 'CAMBIO: RELE ON, LED OFF')
                else:
                    # RELE OFF, LED ON
                    # Hardware "active low": HIGH desactiva relé, LOW enciende LED
                    relay.on()   # HIGH = relé desactivado (OFF)
                    led.off()    # LOW = LED encendido (ON)
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
            # Hardware "active low": HIGH desactiva todo
            relay.on()   # HIGH = relé desactivado
            led.off()    # LOW = LED encendido (mantener visible durante shutdown)
            logger.log('heladera', 'Hardware apagado')
        except:
            pass
    except Exception as e:
        logger.log('heladera', f'ERROR: {e}')
        try:
            sys.print_exception(e)
        except:
            pass
