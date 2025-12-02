# Heladera App - Control basado en hora real
# Hardware "Active Low": LED pin 2, RELE pin 5
# Ciclo: 25min OFF, 15min ON (40min total). 00:00-07:00 siempre OFF
#
# CRÍTICO para WebREPL: El loop debe ceder control frecuentemente.
import sys
try:
    import machine
    import time
    import gc
    import logger
    from heladera import state
except ImportError:
    print("[heladera/app] ERROR: Módulos MicroPython no encontrados")

RELAY_PIN = 5
LED_PIN = 2
CYCLE_DURATION = 40 * 60  # 40 minutos (25 OFF + 15 ON)
CYCLE_OFF_DURATION = 25 * 60  # 25 minutos OFF
NIGHT_START_HOUR = 0
NIGHT_END_HOUR = 7

def _get_cycle_position(tm, has_ntp, cycle_start_time):
    """Retorna posición en ciclo (0-39 minutos). <25=OFF, >=25=ON"""
    if has_ntp:
        total_minutes = tm[3] * 60 + tm[4]
        return total_minutes % 40
    else:
        if cycle_start_time is None:
            return 0
        elapsed = int((time.time() - cycle_start_time) / 60)
        return elapsed % 40

def _should_fridge_be_on(tm, has_ntp, cycle_start_time):
    """Determina si la heladera debe estar ON basado en ciclo y hora"""
    if not has_ntp and cycle_start_time is None:
        return None
    h = tm[3]
    if h >= NIGHT_START_HOUR and h < NIGHT_END_HOUR:
        return False
    pos = _get_cycle_position(tm, has_ntp, cycle_start_time)
    return pos >= 25

def _set_relay_state(relay, led, on):
    """Unifica cambio de estado del relay/LED"""
    if on:
        relay.off()  # Active Low
        led.on()
    else:
        relay.on()
        led.off()

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
        fridge_on, cycle_offset = state.recover_state_after_boot(s, has_ntp)
        
        relay = machine.Pin(RELAY_PIN, machine.Pin.OUT)
        led = machine.Pin(LED_PIN, machine.Pin.OUT)
        _set_relay_state(relay, led, fridge_on)
        
        cycle_start = time.time() - cycle_offset if not has_ntp else None
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
                    should_on = _should_fridge_be_on(tm, has_ntp, cycle_start)
                    if should_on is not None and should_on != fridge_on:
                        fridge_on = should_on
                        _set_relay_state(relay, led, fridge_on)
                        logger.log('heladera', f'{"ON" if fridge_on else "OFF"} {tm[3]:02d}:{tm[4]:02d}')
                        s['fridge_on'] = fridge_on
                        s['last_save_timestamp'] = t
                        state.update_ntp_timestamp(s, t)
                        if not has_ntp:
                            cycle_start = t
                        time.sleep(0)
                except Exception as e:
                    logger.log('heladera', f'ERROR: {e}')
            
            if t - last_save >= 60.0:
                try:
                    state.save_state(s)
                    last_save = t
                    time.sleep(0)
                    gc.collect()
                except:
                    pass
            
            if tick % 1000 == 0:
                try:
                    tm = time.localtime()
                    if has_ntp:
                        logger.log('heladera', f'{"ON" if fridge_on else "OFF"} {tm[3]:02d}:{tm[4]:02d}')
                    else:
                        pos = _get_cycle_position(tm, False, cycle_start)
                        if pos < 25:
                            remaining_min = 25 - pos
                        else:
                            remaining_min = 40 - pos
                        logger.log('heladera', f'{"ON" if fridge_on else "OFF"} {remaining_min:.0f}m (sin NTP)')
                except:
                    pass
            yield
            
    except KeyboardInterrupt:
        logger.log('heladera', 'Interrumpido')
        try:
            _set_relay_state(relay, led, False)
        except:
            pass
    except Exception as e:
        logger.log('heladera', f'ERROR: {e}')
        try:
            sys.print_exception(e)
        except:
            pass
