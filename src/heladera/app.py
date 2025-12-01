# Heladera App
import sys
try:
    import machine
    import time
    import gc
    from heladera import state as state_module
except ImportError:
    print("[heladera/app] ERROR: Módulos MicroPython no encontrados")
RELAY_PIN = 5
LED_PIN = 2
CYCLE_DURATION = 30 * 60
NIGHT_END_HOUR = 7
LED_BLINK_INTERVAL = 0.5
def log(msg):
    print(f'[heladera] {msg}')
    try:
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass
def has_valid_time(last_ntp=0, max_drift=300):
    try:
        import time
        tm = time.localtime()
        if tm[0] < 2020 or tm[0] > 2030:
            return False
        if last_ntp > 0 and (time.time() - last_ntp) > max_drift:
            return False
        return True
    except:
        return False
def is_night_time():
    try:
        return time.localtime()[3] < NIGHT_END_HOUR
    except:
        return False
def is_test_mode_on():
    try:
        return time.localtime()[4] % 2 == 0
    except:
        return True

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

        max_drift = 300
        try:
            max_drift = int(cfg.get('MAX_TIME_DRIFT_SECONDS', '300'))
        except:
            pass

        has_ntp = has_valid_time(persistent_state.get('last_ntp_timestamp', 0), max_drift)
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
            has_ntp = has_valid_time(persistent_state.get('last_ntp_timestamp', 0), max_drift)

            if has_ntp:
                test_on = is_test_mode_on()
                if test_on != fridge_on:
                    fridge_on = test_on
                    if fridge_on:
                        relay.off()
                        led.off()
                        log('TEST: Minuto PAR - Heladera ON')
                    else:
                        relay.on()
                        led.on()
                        log('TEST: Minuto IMPAR - Heladera OFF')
                time.sleep(5)
                continue
            if not has_ntp:
                if current_time - last_blink >= LED_BLINK_INTERVAL:
                    led_state = not led_state
                    led.on() if led_state else led.off()
                    last_blink = current_time
                elapsed = current_time - cycle_start
                if elapsed >= CYCLE_DURATION:
                    fridge_on = not fridge_on
                    relay.off() if fridge_on else relay.on()
                    log(f'Sin NTP - Ciclo: Heladera {"ON" if fridge_on else "OFF"} (30 min)')
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
            if is_night_time():
                if fridge_on:
                    relay.on()
                    led.on()
                    fridge_on = False
                    log('Modo nocturno: heladera apagada (00:00-07:00)')
                time.sleep(60)
                continue
            elapsed = current_time - cycle_start
            if elapsed >= CYCLE_DURATION:
                fridge_on = not fridge_on
                if fridge_on:
                    relay.off()
                    led.off()
                    log('Ciclo: Heladera ON (30 min)')
                else:
                    relay.on()
                    led.on()
                    log('Ciclo: Heladera OFF (30 min)')
                persistent_state['fridge_on'] = fridge_on
                persistent_state['cycle_elapsed_seconds'] = 0
                persistent_state['last_save_timestamp'] = current_time
                if has_ntp:
                    state_module.update_ntp_timestamp(persistent_state, current_time)
                if state_module.save_state(persistent_state):
                    log('Estado guardado ✓')
                else:
                    log('⚠ Fallo al guardar estado')
                cycle_start = current_time
                last_checkpoint_time = current_time
                gc.collect()

            if current_time - last_checkpoint_time >= CHECKPOINT_INTERVAL:
                elapsed = current_time - cycle_start
                persistent_state['cycle_elapsed_seconds'] = elapsed
                persistent_state['last_save_timestamp'] = current_time
                persistent_state['total_runtime_seconds'] += CHECKPOINT_INTERVAL
                if has_ntp:
                    state_module.update_ntp_timestamp(persistent_state, current_time)
                state_module.save_state(persistent_state)
                last_checkpoint_time = current_time
                runtime_hours = persistent_state['total_runtime_seconds'] / 3600
                log(f'Checkpoint: {runtime_hours:.1f}h runtime')
                gc.collect()
            time.sleep(1)

    except KeyboardInterrupt:
        log('Interrumpido por usuario')
        try:
            elapsed = time.time() - cycle_start
            persistent_state['cycle_elapsed_seconds'] = elapsed
            persistent_state['last_save_timestamp'] = time.time()
            if has_valid_time(persistent_state.get('last_ntp_timestamp', 0), max_drift):
                state_module.update_ntp_timestamp(persistent_state, time.time())
            state_module.save_state(persistent_state)
            log('Estado guardado antes de salir ✓')
        except:
            pass
        try:
            relay.on()
            led.off()
        except:
            pass
    except Exception as e:
        log(f'Error: {e}')
        sys.print_exception(e)
