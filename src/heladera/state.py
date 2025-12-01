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
    """
    Recupera estado inteligente tras boot.

    Args:
        state: Estado cargado desde JSON
        has_ntp: True si tenemos NTP válido

    Returns:
        tuple: (fridge_on, cycle_elapsed_seconds)
    """
    import time

    if not has_ntp:
        # SIN NTP: arrancar conservador con 15 min ON
        log("Sin NTP: arrancando con 15 min ON (conservador)")
        state['fridge_on'] = True
        state['cycle_elapsed_seconds'] = 0
        return (True, 0)

    # CON NTP: calcular estado esperado
    current_timestamp = time.time()
    last_save = state['last_save_timestamp']

    if last_save == 0:
        # Nunca tuvo timestamp, primer boot con NTP
        log("Primer boot con NTP, iniciando ciclo")
        state['fridge_on'] = True
        state['cycle_elapsed_seconds'] = 0
        state['last_ntp_timestamp'] = current_timestamp
        return (True, 0)

    time_delta = current_timestamp - last_save

    # Validar coherencia temporal
    if time_delta < 0:
        log(f"WARNING: reloj retrocedió {-time_delta}s")
        state['fridge_on'] = True
        state['cycle_elapsed_seconds'] = 0
        return (True, 0)

    # Corte largo (>2h): resetear ciclo
    if time_delta > 7200:
        log(f"Corte largo detectado ({time_delta/3600:.1f}h), reseteando")
        state['fridge_on'] = True
        state['cycle_elapsed_seconds'] = 0
        state['last_ntp_timestamp'] = current_timestamp
        return (True, 0)

    # Reconstruir estado esperado
    CYCLE_DURATION = 30 * 60  # 30 minutos
    elapsed_total = state['cycle_elapsed_seconds'] + time_delta

    # Calcular cuántos ciclos completos pasaron
    full_cycles = int(elapsed_total / CYCLE_DURATION)
    remainder = elapsed_total % CYCLE_DURATION

    # Determinar estado ON/OFF esperado
    # Si full_cycles es par, estado no cambió
    # Si es impar, estado se invirtió
    fridge_on = state['fridge_on']
    if full_cycles % 2 == 1:
        fridge_on = not fridge_on

    log(f"Recuperando: {time_delta}s pasaron, {full_cycles} ciclos completos")
    log(f"Estado: {'ON' if fridge_on else 'OFF'}, {remainder}s en ciclo")

    state['fridge_on'] = fridge_on
    state['cycle_elapsed_seconds'] = remainder
    # Actualizar last_ntp_timestamp si es significativamente nuevo
    update_ntp_timestamp(state, current_timestamp)

    return (fridge_on, remainder)
