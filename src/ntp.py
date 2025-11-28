# ntp.py - NTP time synchronization
# Minimal module for NTP sync
import sys

def log(msg):
    """Escribe al serial de forma consistente"""
    print(f"[ntp] {msg}")
    try:
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def sync_ntp():
    """Sincroniza NTP"""
    import ntptime
    import utime
    import time
    
    log("=== Sincronizando hora NTP ===")
    
    try:
        tm_before = utime.localtime()
        log(f"Hora actual (antes): {tm_before[3]:02d}:{tm_before[4]:02d}:{tm_before[5]:02d}")
    except:
        pass
    
    for i in range(5):
        try:
            log(f"Intento NTP {i+1}/5...")
            ntptime.settime()
            
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

