# Heladera App - Patrón generador cooperativo
import sys
try:
    import machine
    import time
    import gc
    from heladera import state as state_module
except ImportError:
    print("[heladera/app] ERROR: Módulos MicroPython no encontrados")
RELAY_PIN=5
LED_PIN=2
CYCLE_DURATION=30*60
NIGHT_END_HOUR=7
LED_BLINK_INTERVAL=0.5
def log(msg):
    print(f'[heladera] {msg}')
    try:
        if hasattr(sys.stdout,'flush'):sys.stdout.flush()
    except:pass
def has_valid_time(last_ntp=0,max_drift=300):
    try:
        tm=time.localtime()
        if tm[0]<2020 or tm[0]>2030:return False
        if last_ntp>0 and (time.time()-last_ntp)>max_drift:return False
        return True
    except:return False
def is_night_time():
    try:return time.localtime()[3]<NIGHT_END_HOUR
    except:return False
def is_test_mode_on():
    try:return time.localtime()[4]%2==0
    except:return True
def run(cfg):
    """Generador cooperativo - yield cada tick (~100ms desde main.py)"""
    log('=== Heladera App ===')
    gc.collect()
    try:
        relay=machine.Pin(RELAY_PIN,machine.Pin.OUT)
        led=machine.Pin(LED_PIN,machine.Pin.OUT)
        relay.on()
        led.on()
        log('Hardware OK')
        gc.collect()
        persistent_state=state_module.load_state()
        log(f"Boot #{persistent_state['boot_count']}")
        # Blink inicial (0.6s total)
        for _ in range(3):
            led.off()
            for _ in range(10):yield  # 100ms
            led.on()
            for _ in range(10):yield  # 100ms
        max_drift=300
        try:max_drift=int(cfg.get('MAX_TIME_DRIFT_SECONDS','300'))
        except:pass
        has_ntp=has_valid_time(persistent_state.get('last_ntp_timestamp',0),max_drift)
        fridge_on,cycle_elapsed=state_module.recover_state_after_boot(persistent_state,has_ntp)
        if fridge_on:
            relay.off()
            led.off()
        else:
            relay.on()
            led.on()
        log(f"Estado: {'ON' if fridge_on else 'OFF'}")
        cycle_start=time.time()-cycle_elapsed
        last_checkpoint_time=time.time()
        CHECKPOINT_INTERVAL=10*60
        last_blink=time.time()
        led_state=True
        log('Loop OK')
        # Contadores para delays cooperativos
        test_ticks=0  # Contador para delay de 5s en test mode
        night_ticks=0  # Contador para delay de 60s en night mode
        # Loop cooperativo principal
        while True:
            current_time=time.time()
            has_ntp=has_valid_time(persistent_state.get('last_ntp_timestamp',0),max_drift)
            # TEST MODE: verificar cada 5s (50 ticks)
            if has_ntp:
                test_ticks+=1
                if test_ticks>=50:  # 50 ticks × 100ms = 5s
                    test_ticks=0
                    test_on=is_test_mode_on()
                    if test_on!=fridge_on:
                        fridge_on=test_on
                        if fridge_on:
                            relay.off()
                            led.off()
                            log('TEST: Minuto PAR - Heladera ON')
                        else:
                            relay.on()
                            led.on()
                            log('TEST: Minuto IMPAR - Heladera OFF')
                yield
                continue
            # SIN NTP: blink LED + ciclos 30min
            if not has_ntp:
                # LED blink cada 0.5s
                if current_time-last_blink>=LED_BLINK_INTERVAL:
                    led_state=not led_state
                    led.on() if led_state else led.off()
                    last_blink=current_time
                # Verificar ciclo 30min
                elapsed=current_time-cycle_start
                if elapsed>=CYCLE_DURATION:
                    fridge_on=not fridge_on
                    if fridge_on:
                        relay.off()
                        led.off()
                    else:
                        relay.on()
                        led.on()
                    log(f'Sin NTP - Ciclo: Heladera {"ON" if fridge_on else "OFF"} (30 min)')
                    persistent_state['fridge_on']=fridge_on
                    persistent_state['cycle_elapsed_seconds']=0
                    persistent_state['last_save_timestamp']=current_time
                    if state_module.save_state(persistent_state):log('Estado guardado ✓')
                    else:log('⚠ Fallo al guardar estado')
                    cycle_start=current_time
                    last_checkpoint_time=current_time
                    gc.collect()
                yield
                continue
            # MODO NOCTURNO: verificar cada 60s (600 ticks)
            if is_night_time():
                night_ticks+=1
                if night_ticks>=600:  # 600 ticks × 100ms = 60s
                    night_ticks=0
                    if fridge_on:
                        relay.on()
                        led.on()
                        fridge_on=False
                        log('Modo nocturno: heladera apagada (00:00-07:00)')
                yield
                continue
            # MODO NORMAL: ciclos 30min + checkpoints
            night_ticks=0  # Reset cuando salimos de modo nocturno
            elapsed=current_time-cycle_start
            if elapsed>=CYCLE_DURATION:
                fridge_on=not fridge_on
                if fridge_on:
                    relay.off()
                    led.off()
                    log('Ciclo: Heladera ON (30 min)')
                else:
                    relay.on()
                    led.on()
                    log('Ciclo: Heladera OFF (30 min)')
                persistent_state['fridge_on']=fridge_on
                persistent_state['cycle_elapsed_seconds']=0
                persistent_state['last_save_timestamp']=current_time
                if has_ntp:state_module.update_ntp_timestamp(persistent_state,current_time)
                if state_module.save_state(persistent_state):log('Estado guardado ✓')
                else:log('⚠ Fallo al guardar estado')
                cycle_start=current_time
                last_checkpoint_time=current_time
                gc.collect()
            # Checkpoint cada 10 min
            if current_time-last_checkpoint_time>=CHECKPOINT_INTERVAL:
                elapsed=current_time-cycle_start
                persistent_state['cycle_elapsed_seconds']=elapsed
                persistent_state['last_save_timestamp']=current_time
                persistent_state['total_runtime_seconds']+=CHECKPOINT_INTERVAL
                if has_ntp:state_module.update_ntp_timestamp(persistent_state,current_time)
                state_module.save_state(persistent_state)
                last_checkpoint_time=current_time
                runtime_hours=persistent_state['total_runtime_seconds']/3600
                log(f'Checkpoint: {runtime_hours:.1f}h runtime')
                gc.collect()
            yield  # Liberar control a main.py
    except KeyboardInterrupt:
        log('Interrumpido por usuario')
        try:
            elapsed=time.time()-cycle_start
            persistent_state['cycle_elapsed_seconds']=elapsed
            persistent_state['last_save_timestamp']=time.time()
            if has_valid_time(persistent_state.get('last_ntp_timestamp',0),max_drift):
                state_module.update_ntp_timestamp(persistent_state,time.time())
            state_module.save_state(persistent_state)
            log('Estado guardado antes de salir ✓')
        except:pass
        try:
            relay.off()
            led.off()
        except:pass
    except Exception as e:
        log(f'Error: {e}')
        sys.print_exception(e)
