# Heladera App - Control basado en hora real
# Hardware "Active Low": LED pin 2, RELE pin 5
# Ciclo: 18min OFF, 12min ON (30min total). 01:30-07:00 siempre OFF
# Ciclo se reinicia cada hora (minutos 0-29 y 30-59) con NTP
#
# CRÍTICO para WebREPL: El loop debe ceder control frecuentemente.
import sys
try:
    import machine
    import time
    import gc
    import logger
    from heladera import state
    # Night hours constants imported from state.py to ensure consistency
    from heladera.state import NIGHT_START_HOUR, NIGHT_START_MINUTE, NIGHT_END_HOUR
    import ntp
except ImportError:
    print("[heladera/app] ERROR: Módulos MicroPython no encontrados")
    # Fallback values if import fails (should not happen in normal operation)
    NIGHT_START_HOUR = 1
    NIGHT_START_MINUTE = 30
    NIGHT_END_HOUR = 7

RELAY_PIN = 5
LED_PIN = 2
CYCLE_DURATION = 30 * 60  # 30 minutos (18 OFF + 12 ON)
CYCLE_OFF_DURATION = 18 * 60  # 18 minutos OFF

def _get_cycle_position(tm, has_ntp, cycle_start_time):
    """Retorna posición en ciclo (0-29 minutos). <18=OFF, >=18=ON"""
    if has_ntp:
        return tm[4] % 30
    else:
        if cycle_start_time is None:
            return 0
        elapsed = int((time.time() - cycle_start_time) / 60)
        return elapsed % 30

def _should_fridge_be_on(tm, has_ntp, cycle_start_time):
    """Determina si la heladera debe estar ON basado en ciclo y hora"""
    if not has_ntp and cycle_start_time is None:
        return None
    if has_ntp:
        h, m = tm[3], tm[4]
        if (h == NIGHT_START_HOUR and m >= NIGHT_START_MINUTE) or (h > NIGHT_START_HOUR and h < NIGHT_END_HOUR):
            return False
    pos = _get_cycle_position(tm, has_ntp, cycle_start_time)
    return pos >= 18

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
        last_ntp_check = time.time()  # Verificación periódica de NTP
        tick = 0
        
        while True:
            t = time.time()
            tick += 1
            
            # Re-evaluar RTC cada 5 min (mantiene tiempo sin WiFi)
            if t - last_ntp_check >= 300.0:
                last_ntp_check = t
                new_has_ntp, drift_detected = ntp.check_ntp_status(cfg, s, 'heladera')
                
                # Actualizar timestamps si NTP válido y sin drift (nueva línea base)
                if new_has_ntp and not drift_detected:
                    state.update_ntp_timestamp(s, t)
                
                if new_has_ntp != has_ntp or drift_detected:
                    old_has_ntp = has_ntp
                    has_ntp = new_has_ntp and not drift_detected
                    if old_has_ntp != has_ntp:
                        if has_ntp:
                            logger.log('heladera', '✓ RTC válido, hora real')
                            cycle_start = None
                        else:
                            logger.log('heladera', '⚠ RTC inválido, ciclo relativo')
                            cycle_start = time.time()
            
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
                        state.update_ntp_timestamp(s, t)
                        if not has_ntp:
                            cycle_start = t
                        time.sleep(0)
                except Exception as e:
                    logger.log('heladera', f'ERROR: {e}')
            
            if t - last_save >= 60.0:
                try:
                    if state.save_state(s):
                        # Actualizar timestamp solo después de guardar exitosamente
                        s['last_save_timestamp'] = t
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
                        if pos < 18:
                            remaining_min = 18 - pos
                        else:
                            remaining_min = 30 - pos
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