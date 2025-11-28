# ntp.py - NTP time synchronization with timezone adjustment
import sys

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[ntp] {msg}")
    try:
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def sync_ntp(longitude=None):
    """
    Sincroniza NTP y ajusta timezone automáticamente.

    Args:
        longitude: Longitud para calcular timezone (default: desde config)

    Returns:
        bool: True si sincronización exitosa
    """
    import ntptime
    import utime
    import time

    log("=== Sincronizando hora NTP ===")

    # Calcular timezone offset
    tz_offset = 0
    if longitude is not None:
        from . import timezone as tz_module
        tz_offset = tz_module.get_timezone_offset(longitude)
        log(f"Timezone offset: UTC{tz_offset:+d}")

    try:
        tm_before = utime.localtime()
        log(f"Hora actual (antes): {tm_before[3]:02d}:{tm_before[4]:02d}:{tm_before[5]:02d}")
    except:
        pass

    for i in range(5):
        try:
            log(f"Intento NTP {i+1}/5...")
            ntptime.settime()

            # Aplicar timezone offset al RTC
            if tz_offset != 0:
                import machine
                rtc = machine.RTC()
                current_time = utime.time()
                adjusted_time = current_time + (tz_offset * 3600)
                rtc.datetime(utime.localtime(adjusted_time))

            try:
                tm_after = utime.localtime()
                log(f"Hora sincronizada: {tm_after[3]:02d}:{tm_after[4]:02d}:{tm_after[5]:02d}")
                log(f"Fecha: {tm_after[2]:02d}/{tm_after[1]:02d}/{tm_after[0]}")
            except:
                pass

            log("✓ NTP sincronizado exitosamente")
            log("=== Sincronización NTP completada ===")
            return True
        except Exception as e:
            log(f"✗ NTP intento {i+1}/5 falló: {e}")
            if i < 4:
                time.sleep(2)

    log("✗ NTP FAIL - No se pudo sincronizar después de 5 intentos")
    log("=== Fallo de sincronización NTP ===")
    return False

