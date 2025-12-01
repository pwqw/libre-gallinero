# Heladera App - Control basado en hora real
# Hardware "Active Low": LED pin 2, RELE pin 5
# Con NTP: 0-29min OFF, 30-59min ON. 00:00-07:00 siempre OFF
# Sin NTP: ciclos ~30min con drift
import sys
try:
    import machine
    import time
    import gc
    import logger
    import state
except ImportError:
    print("[heladera/app] ERROR: Módulos MicroPython no encontrados")

RELAY_PIN = 5
LED_PIN = 2
CYCLE_DURATION_NO_NTP = 30 * 60  # 30 minutos sin NTP
NIGHT_START_HOUR = 0
NIGHT_END_HOUR = 7

def _should_fridge_be_on(tm, has_ntp):
    if not has_ntp:
        return None
    h = tm[3]
    m = tm[4]
    if h >= NIGHT_START_HOUR and h < NIGHT_END_HOUR:
        return False
    return m >= 30

def run(cfg):
    logger.log('heladera', '=== Heladera App ===')
    gc.collect()
    try:
        has_ntp = False
        try:
            tm = time.localtime()
            if tm[0] >= 2020:
                has_ntp = True
                logger.log('heladera', f'NTP: {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}')
        except:
            pass
        s = state.load_state()
        logger.log('heladera', f'Boot #{s["boot_count"]}')
        if has_ntp:
            fridge_on, _ = state.recover_state_after_boot(s, True)
        else:
            fridge_on, _ = state.recover_state_after_boot(s, False)
        relay = machine.Pin(RELAY_PIN, machine.Pin.OUT)
        led = machine.Pin(LED_PIN, machine.Pin.OUT)
        if fridge_on:
            relay.off()
            led.on()
        else:
            relay.on()
            led.off()
        cycle_start = time.time() if not has_ntp else None
        last_check = time.time()
        last_save = time.time()
        tick = 0
        
        while True:
            t = time.time()
            tick += 1
            if t - last_check >= 1.0:
                last_check = t
                try:
                    tm = time.localtime()
                    should_on = _should_fridge_be_on(tm, has_ntp)
                    if has_ntp and should_on is not None:
                        if should_on != fridge_on:
                            fridge_on = should_on
                            if fridge_on:
                                relay.off()
                                led.on()
                                logger.log('heladera', f'ON {tm[3]:02d}:{tm[4]:02d}')
                            else:
                                relay.on()
                                led.off()
                                logger.log('heladera', f'OFF {tm[3]:02d}:{tm[4]:02d}')
                            s['fridge_on'] = fridge_on
                            s['cycle_elapsed_seconds'] = 0
                            s['last_save_timestamp'] = t
                            state.update_ntp_timestamp(s, t)
                    elif not has_ntp:
                        if cycle_start is None:
                            cycle_start = t
                        elapsed = t - cycle_start
                        if elapsed >= CYCLE_DURATION_NO_NTP:
                            fridge_on = not fridge_on
                            cycle_start = t
                            if fridge_on:
                                relay.off()
                                led.on()
                                logger.log('heladera', 'ON (sin NTP)')
                            else:
                                relay.on()
                                led.off()
                                logger.log('heladera', 'OFF (sin NTP)')
                            s['fridge_on'] = fridge_on
                            s['cycle_elapsed_seconds'] = 0
                            s['last_save_timestamp'] = t
                        else:
                            s['cycle_elapsed_seconds'] = elapsed
                except Exception as e:
                    logger.log('heladera', f'ERROR: {e}')
            if t - last_save >= 60.0:
                try:
                    state.save_state(s)
                    last_save = t
                except:
                    pass
            if tick % 1000 == 0:
                try:
                    tm = time.localtime()
                    if has_ntp:
                        logger.log('heladera', f'{"ON" if fridge_on else "OFF"} {tm[3]:02d}:{tm[4]:02d}')
                    else:
                        e = t - cycle_start if cycle_start else 0
                        r = CYCLE_DURATION_NO_NTP - e
                        logger.log('heladera', f'{"ON" if fridge_on else "OFF"} {r:.0f}s (sin NTP)')
                except:
                    pass
            yield
            
    except KeyboardInterrupt:
        logger.log('heladera', 'Interrumpido')
        try:
            relay.on()
            led.off()
        except:
            pass
    except Exception as e:
        logger.log('heladera', f'ERROR: {e}')
        try:
            sys.print_exception(e)
        except:
            pass
