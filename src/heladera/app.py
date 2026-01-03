# Heladera App - Control basado en hora real
# Hardware "Active Low": LED pin 2, RELE pin 5
# Ciclo normal: 18min OFF, 12min ON (30min total). 01:30-07:00 siempre OFF
# Ciclo modo helado: 10min OFF, 10min ON (20min total). Sin horario nocturno
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

# Constantes de ciclo
CYCLE_NORMAL_TOTAL = 30  # 30 minutos: 18 OFF + 12 ON
CYCLE_NORMAL_OFF_UNTIL = 18  # OFF hasta minuto 18, luego ON
CYCLE_HELADO_TOTAL = 20  # 20 minutos: 10 OFF + 10 ON
CYCLE_HELADO_OFF_UNTIL = 10  # OFF hasta minuto 10, luego ON

def _is_modo_helado(cfg):
    """Verifica si el modo helado está activo desde configuración"""
    modo_helado = cfg.get('HELADERA_MODO_HELADO', 'false').lower()
    return modo_helado in ('true', '1', 'yes', 'on')

def _get_cycle_position(tm, has_ntp, cycle_start_time, modo_helado):
    """Retorna posición en ciclo.
    Normal: 0-29 minutos (<18=OFF, >=18=ON)
    Helado: 0-19 minutos (<10=OFF, >=10=ON)
    """
    cycle_total = CYCLE_HELADO_TOTAL if modo_helado else CYCLE_NORMAL_TOTAL
    if has_ntp:
        return tm[4] % cycle_total
    else:
        if cycle_start_time is None:
            return 0
        elapsed = int((time.time() - cycle_start_time) / 60)
        return elapsed % cycle_total

def _should_fridge_be_on(tm, has_ntp, cycle_start_time, modo_helado):
    """Determina si la heladera debe estar ON basado en ciclo y hora"""
    if not has_ntp and cycle_start_time is None:
        return None
    # En modo helado, ignorar horario nocturno
    if has_ntp and not modo_helado:
        h, m = tm[3], tm[4]
        if (h == NIGHT_START_HOUR and m >= NIGHT_START_MINUTE) or (h > NIGHT_START_HOUR and h < NIGHT_END_HOUR):
            return False
    pos = _get_cycle_position(tm, has_ntp, cycle_start_time, modo_helado)
    if modo_helado:
        return pos >= CYCLE_HELADO_OFF_UNTIL
    else:
        return pos >= CYCLE_NORMAL_OFF_UNTIL

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
        modo_helado = _is_modo_helado(cfg)
        if modo_helado:
            logger.log('heladera', 'Modo HELADO: 10min ON/10min OFF, sin horario nocturno')
        else:
            logger.log('heladera', 'Modo NORMAL: 12min ON/18min OFF, descanso 01:30-07:00')
        
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
        fridge_on, cycle_offset = state.recover_state_after_boot(s, has_ntp, modo_helado)
        
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
                    # Re-evaluar modo helado desde config (permite cambios dinámicos)
                    modo_helado = _is_modo_helado(cfg)
                    tm = time.localtime()
                    should_on = _should_fridge_be_on(tm, has_ntp, cycle_start, modo_helado)
                    if should_on is not None and should_on != fridge_on:
                        fridge_on = should_on
                        _set_relay_state(relay, led, fridge_on)
                        logger.log('heladera', f'{"ON" if fridge_on else "OFF"} {tm[3]:02d}:{tm[4]:02d}')
                        s['fridge_on'] = fridge_on
                        if not has_ntp:
                            cycle_start = t
                        time.sleep(0)
                except Exception as e:
                    logger.log('heladera', f'ERROR: {e}')
            
            if t - last_save >= 60.0:
                try:
                    # NO actualizar last_save_timestamp aquí: update_ntp_timestamp()
                    # ya mantiene ambos timestamps sincronizados. Sobrescribirlo aquí
                    # rompería la invariante requerida por la detección de drift en ntp.py.
                    # La lógica de drift calcula: expected_time = last_ntp_timestamp + 
                    # (current_time - last_save_timestamp), por lo que ambos deben
                    # establecerse simultáneamente cuando se actualiza NTP.
                    state.save_state(s)
                    last_save = t
                    time.sleep(0)
                    gc.collect()
                except:
                    pass
            
            if tick % 1000 == 0:
                try:
                    modo_helado = _is_modo_helado(cfg)
                    tm = time.localtime()
                    if has_ntp:
                        logger.log('heladera', f'{"ON" if fridge_on else "OFF"} {tm[3]:02d}:{tm[4]:02d}')
                    else:
                        pos = _get_cycle_position(tm, False, cycle_start, modo_helado)
                        cycle_total = CYCLE_HELADO_TOTAL if modo_helado else CYCLE_NORMAL_TOTAL
                        off_until = CYCLE_HELADO_OFF_UNTIL if modo_helado else CYCLE_NORMAL_OFF_UNTIL
                        if pos < off_until:
                            remaining_min = off_until - pos
                        else:
                            remaining_min = cycle_total - pos
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