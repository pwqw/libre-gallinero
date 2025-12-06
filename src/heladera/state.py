# state.py - State persistence for heladera app
#
# Maneja la persistencia del estado de la heladera en flash (/state.json)
# para mantener ciclos a través de reinicios y cortes de luz.
import sys

try:
    import ujson as json
except ImportError:
    import json

STATE_FILE = '/state.json'
STATE_FILE_TMP = '/state.json.tmp'

# Night hours boundary constants (shared with app.py)
NIGHT_START_HOUR = 1
NIGHT_START_MINUTE = 30
NIGHT_END_HOUR = 7

def log(msg):
    """Log with module prefix"""
    print(f'[heladera/state] {msg}')
    try:
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def get_default_state():
    """Retorna estado por defecto para primer boot"""
    return {
        'version': 1,
        'last_ntp_timestamp': 0,
        'last_save_timestamp': 0,
        'fridge_on': True,
        'cycle_elapsed_seconds': 0,
        'total_runtime_seconds': 0,
        'boot_count': 0
    }

def validate_state(state):
    """Valida estructura del estado cargado"""
    required_keys = [
        'version', 'last_ntp_timestamp', 'last_save_timestamp',
        'fridge_on', 'cycle_elapsed_seconds', 'total_runtime_seconds',
        'boot_count'
    ]
    return all(k in state for k in required_keys)

def load_state():
    """Carga estado desde /state.json, retorna defaults si falla"""
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)

        # Validar estructura
        if not validate_state(state):
            log("Estado inválido, usando defaults")
            return get_default_state()

        # Incrementar boot counter
        state['boot_count'] += 1
        log(f"Estado cargado (boot #{state['boot_count']})")
        return state

    except OSError:
        # Archivo no existe (primer boot)
        log("Primer boot, creando estado inicial")
        return get_default_state()

    except Exception as e:
        log(f"Error cargando estado: {e}, usando defaults")
        return get_default_state()

def save_state(state):
    """Guarda estado a /state.json con protección anti-corrupción"""
    try:
        import os
        import gc

        # Escribir a archivo temporal
        with open(STATE_FILE_TMP, 'w') as f:
            json.dump(state, f)

        # Rename atómico (sobrescribe state.json existente)
        try:
            os.remove(STATE_FILE)
        except OSError:
            pass  # No existe, ok

        os.rename(STATE_FILE_TMP, STATE_FILE)

        gc.collect()
        return True

    except OSError as e:
        if e.args[0] == 28:  # ENOSPC
            log("ERROR: Flash lleno")
        else:
            log(f"ERROR guardando: {e}")
        return False

    except Exception as e:
        log(f"ERROR inesperado: {e}")
        return False

def update_ntp_timestamp(state, ts):
    # Actualiza last_ntp_timestamp con timestamp actual
    state['last_ntp_timestamp'] = ts

def recover_state_after_boot(state, has_ntp):
    """Recupera estado tras boot usando misma lógica de ciclo"""
    import time
    
    if not has_ntp:
        current_timestamp = time.time()
        last_save = state['last_save_timestamp']
        
        if last_save == 0 or current_timestamp - last_save > 7200:
            log("Sin NTP: resetear ciclo (12 min ON)")
            state['fridge_on'] = True
            state['cycle_elapsed_seconds'] = 0
            state['last_save_timestamp'] = current_timestamp
            return (True, 0)
        
        time_delta = current_timestamp - last_save
        if time_delta < 0:
            log("WARNING: reloj retrocedió")
            return (True, 0)
        
        # Calcular posición en ciclo de 30 min
        elapsed_total = state['cycle_elapsed_seconds'] + time_delta
        pos = int(elapsed_total / 60) % 30
        fridge_on = pos >= 18
        
        remainder = elapsed_total % (30 * 60)
        log(f"Sin NTP: {'ON' if fridge_on else 'OFF'}, {remainder//60:.0f}m en ciclo")
        
        state['fridge_on'] = fridge_on
        state['cycle_elapsed_seconds'] = remainder
        state['last_save_timestamp'] = current_timestamp
        return (fridge_on, remainder)
    
    # CON NTP
    try:
        tm = time.localtime()
        h, m = tm[3], tm[4]
        
        if (h == NIGHT_START_HOUR and m >= NIGHT_START_MINUTE) or (h > NIGHT_START_HOUR and h < NIGHT_END_HOUR):
            log(f"Nocturno ({h:02d}:{m:02d}): OFF")
            state['fridge_on'] = False
            state['cycle_elapsed_seconds'] = 0
            state['last_ntp_timestamp'] = time.time()
            state['last_save_timestamp'] = time.time()
            return (False, 0)
        
        # Misma lógica que app.py (ciclo reinicia cada hora)
        pos = m % 30
        fridge_on = pos >= 18
        
        log(f"Hora ({h:02d}:{m:02d}): {'ON' if fridge_on else 'OFF'}")
        state['fridge_on'] = fridge_on
        state['cycle_elapsed_seconds'] = 0
        state['last_ntp_timestamp'] = time.time()
        state['last_save_timestamp'] = time.time()
        return (fridge_on, 0)
    
    except Exception as e:
        log(f"ERROR: {e}, usando estado guardado")
        return (state.get('fridge_on', True), state.get('cycle_elapsed_seconds', 0))
