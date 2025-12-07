# ntp.py - NTP sync w/timezone
import logger
def log(msg):
 logger.log('ntp',msg)

def sync_ntp(tz_offset=0):
    import ntptime,utime,time
    log("=== NTP ===")
    if tz_offset!=0:
        log(f"TZ:UTC{tz_offset:+d}")
    try:
        tm=utime.localtime()
        log(f"Pre:{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d} {tm[2]:02d}/{tm[1]:02d}/{tm[0]}")
    except:pass
    for i in range(5):
        try:
            log(f"NTP {i+1}/5")
            ntptime.settime()
            timestamp_utc=utime.time()
            if tz_offset!=0:
                timestamp_local=timestamp_utc+(tz_offset*3600)
                import machine
                rtc=machine.RTC()
                tm_local=utime.localtime(timestamp_local)
                rtc.datetime((tm_local[0],tm_local[1],tm_local[2],tm_local[6],tm_local[3],tm_local[4],tm_local[5],0))
            tm=utime.localtime()
            log(f"Local:{tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d} {tm[2]:02d}/{tm[1]:02d}/{tm[0]}")
            tm_utc=utime.localtime(timestamp_utc)
            log(f"UTC:{tm_utc[3]:02d}:{tm_utc[4]:02d}:{tm_utc[5]:02d} {tm_utc[2]:02d}/{tm_utc[1]:02d}/{tm_utc[0]}")
            log("✓ OK")
            return (True,timestamp_utc)
        except Exception as e:
            log(f"✗ {i+1}/5:{e}")
            if i<4:time.sleep(2)
    log("✗ FAIL")
    return (False,0)

def check_ntp_status(cfg, state_dict=None, log_tag='ntp'):
    """
    Re-evalúa el estado de NTP y detecta drift del reloj.
    Función común para todas las apps.
    
    Args:
        cfg: Diccionario de configuración (debe tener MAX_TIME_DRIFT_SECONDS)
        state_dict: Diccionario de estado con last_ntp_timestamp y last_save_timestamp (opcional)
        log_tag: Tag para logging (default: 'ntp')
    
    Returns:
        tuple: (has_ntp: bool, drift_detected: bool)
    """
    import time
    try:
        tm = time.localtime()
        current_year = tm[0]
        
        # Verificar si el año es válido (indica NTP sincronizado)
        ntp_valid = current_year >= 2020 and current_year <= 2030
        
        # Cargar MAX_TIME_DRIFT_SECONDS desde configuración
        max_drift = 300  # default 5 minutos
        try:
            drift_str = cfg.get('MAX_TIME_DRIFT_SECONDS', '300')
            max_drift = int(drift_str)
        except:
            pass
        
        # Verificar drift comparando tiempo actual con last_ntp_timestamp
        # Optimizado para MicroPython 1.19: cachear time.time() una sola vez
        drift_detected = False
        if state_dict:
            last_ntp_ts = state_dict.get('last_ntp_timestamp', 0)
            if last_ntp_ts > 0:
                current_time = time.time()  # Llamar una sola vez
                last_save_ts = state_dict.get('last_save_timestamp', current_time)
                
                # Calcular tiempo esperado: last_ntp_timestamp + tiempo transcurrido desde last_save
                elapsed_since_save = current_time - last_save_ts
                expected_time = last_ntp_ts + elapsed_since_save
                time_drift = abs(current_time - expected_time)
                
                if time_drift > max_drift:
                    drift_detected = True
                    logger.log(log_tag, f'⚠ Drift: {int(time_drift)}s (max: {max_drift}s)')
        
        return (ntp_valid, drift_detected)
    except Exception as e:
        logger.log(log_tag, f'Error verificando NTP: {e}')
        return (False, False)
