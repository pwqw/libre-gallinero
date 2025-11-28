# Heladera App - Refrigerator automation with timed cycles
# D1 (GPIO5) -> Relay IN (NC), D2 (GPIO2) -> LED, GND -> Relay GND, VIN (5V) -> Relay VCC
import sys

try:
    import machine
    import time
    import gc
    from . import state as state_module
except ImportError:
    print("[heladera/app] ERROR: Módulos MicroPython no encontrados")

RELAY_PIN = 5
LED_PIN = 2
CYCLE_DURATION = 30 * 60
NIGHT_START_HOUR = 0
NIGHT_END_HOUR = 7
LED_BLINK_INTERVAL = 0.5

def log(msg):
    """Log with module prefix"""
    print(f'[heladera] {msg}')
    try:
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def has_valid_time():
    try:
        return time.localtime()[0] > 2020
    except:
        return False

def is_night_time():
    """Check if current time is in night period (00:00-07:00)"""
    try:
        hour = time.localtime()[3]
        # Night period: 00:00 (0) to 06:59 (6)
        return hour < NIGHT_END_HOUR
    except:
        return False

def run(cfg):
    log('=== Heladera App ===')
    gc.collect()

    try:
        relay = machine.Pin(RELAY_PIN, machine.Pin.OUT)
        led = machine.Pin(LED_PIN, machine.Pin.OUT)
        relay.off()
        led.on()
        log('Hardware OK')
        gc.collect()

        persistent_state = state_module.load_state()
        log(f"Boot #{persistent_state['boot_count']}")

        for _ in range(3):
            led.off()
            time.sleep(0.1)
            led.on()
            time.sleep(0.1)

        has_ntp = has_valid_time()
        fridge_on, cycle_elapsed = state_module.recover_state_after_boot(persistent_state, has_ntp)

        if fridge_on:
            relay.off()
            led.off()
        else:
            relay.on()
            led.on()
        log(f"Estado: {'ON' if fridge_on else 'OFF'}")

        cycle_start = time.time() - cycle_elapsed
        last_checkpoint_time = time.time()
        CHECKPOINT_INTERVAL = 10 * 60
        last_blink = time.time()
        led_state = True
        log('Loop OK')

        while True:
            current_time = time.time()
            has_ntp = has_valid_time()

            # Modo degradado: sin NTP - ciclo continuo sin descanso
            if not has_ntp:
                # Parpadear LED cada 0.5s para indicar sin NTP
                if current_time - last_blink >= LED_BLINK_INTERVAL:
                    led_state = not led_state
                    if led_state:
                        led.on()
                    else:
                        led.off()
                    last_blink = current_time

                # Ciclo 30min ON/OFF sin importar la hora
                elapsed = current_time - cycle_start
                if elapsed >= CYCLE_DURATION:
                    fridge_on = not fridge_on

                    if fridge_on:
                        relay.off()  # NC: LOW = ON
                        log('Sin NTP - Ciclo: Heladera ON (30 min)')
                    else:
                        relay.on()   # NC: HIGH = OFF
                        log('Sin NTP - Ciclo: Heladera OFF (30 min)')

                    # Guardar estado en cambio de ciclo
                    persistent_state['fridge_on'] = fridge_on
                    persistent_state['cycle_elapsed_seconds'] = 0
                    persistent_state['last_save_timestamp'] = current_time
                    if state_module.save_state(persistent_state):
                        log('Estado guardado ✓')
                    else:
                        log('⚠ Fallo al guardar estado')

                    cycle_start = current_time
                    last_checkpoint_time = current_time
                    gc.collect()

                time.sleep(0.1)
                continue

            # Con NTP: verificar si es de noche
            if is_night_time():
                # Descanso nocturno: apagar heladera
                if fridge_on:
                    relay.on()  # NC: HIGH = OFF
                    led.on()    # LED encendido = heladera apagada
                    fridge_on = False
                    log('Modo nocturno: heladera apagada (00:00-07:00)')

                time.sleep(60)  # Revisar cada minuto
                continue

            # Modo día: ciclo 30min ON/OFF
            elapsed = current_time - cycle_start

            if elapsed >= CYCLE_DURATION:
                # Cambiar estado del ciclo
                fridge_on = not fridge_on

                if fridge_on:
                    relay.off()  # NC: LOW = ON
                    led.off()    # LED apagado = heladera encendida
                    log('Ciclo: Heladera ON (30 min)')
                else:
                    relay.on()   # NC: HIGH = OFF
                    led.on()     # LED encendido = heladera apagada
                    log('Ciclo: Heladera OFF (30 min)')

                # Guardar estado en cambio de ciclo
                persistent_state['fridge_on'] = fridge_on
                persistent_state['cycle_elapsed_seconds'] = 0
                persistent_state['last_save_timestamp'] = current_time
                if has_ntp:
                    persistent_state['last_ntp_timestamp'] = current_time

                if state_module.save_state(persistent_state):
                    log('Estado guardado ✓')
                else:
                    log('⚠ Fallo al guardar estado')

                cycle_start = current_time
                last_checkpoint_time = current_time
                gc.collect()

            # Checkpoint cada 10 minutos
            if current_time - last_checkpoint_time >= CHECKPOINT_INTERVAL:
                elapsed = current_time - cycle_start
                persistent_state['cycle_elapsed_seconds'] = elapsed
                persistent_state['last_save_timestamp'] = current_time
                persistent_state['total_runtime_seconds'] += CHECKPOINT_INTERVAL

                if has_ntp:
                    persistent_state['last_ntp_timestamp'] = current_time

                state_module.save_state(persistent_state)
                last_checkpoint_time = current_time

                runtime_hours = persistent_state['total_runtime_seconds'] / 3600
                log(f'Checkpoint: {runtime_hours:.1f}h runtime')
                gc.collect()

            # Esperar un poco antes del siguiente check
            time.sleep(1)

    except KeyboardInterrupt:
        log('Interrumpido por usuario')

        # Guardar estado antes de salir
        try:
            elapsed = time.time() - cycle_start
            persistent_state['cycle_elapsed_seconds'] = elapsed
            persistent_state['last_save_timestamp'] = time.time()
            if has_valid_time():
                persistent_state['last_ntp_timestamp'] = time.time()
            state_module.save_state(persistent_state)
            log('Estado guardado antes de salir ✓')
        except:
            pass

        # Apagar heladera y LED al salir
        try:
            relay.on()
            led.off()
        except:
            pass
    except Exception as e:
        log(f'Error: {e}')
        sys.print_exception(e)
