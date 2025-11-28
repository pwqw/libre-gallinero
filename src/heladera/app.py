# Heladera App - Refrigerator automation with timed cycles
#
# Controla heladera con ciclo de 30 min ON/OFF durante el día
# Descanso nocturno: 00:00-07:00 (sin ruido)
# LED integrado indica estado
#
#  +---------------------------------------------------+
#  |                                                   |
#  |   NodeMCU ESP-12E (ESP8266)                       |
#  |                                                   |
#  |  [ ] = Pin usado                                  |
#  |                                                   |
#  |         [D1] (GPIO5)  <--- Relay IN (NC)          |
#  |         [D2] (GPIO2)  <--- LED integrado          |
#  |                                                   |
#  |         [GND] --------+--- Relay GND              |
#  |         [VIN] (5V) ------- Relay VCC              |
#  |                                                   |
#  +---------------------------------------------------+
#  Pines usados:
#    D1 (GPIO5)  -> Relay IN (Normally Closed)
#    D2 (GPIO2)  -> LED integrado (status indicator)
#    GND         -> Relay GND
#    VIN (5V)    -> Relay VCC
import sys

try:
    import machine
    import time
    import gc
except ImportError:
    print("[heladera/app] ERROR: Módulos MicroPython no encontrados")

# Hardware pins
RELAY_PIN = 5   # D1 - Relay control (NC)
LED_PIN = 2     # D2 - Built-in LED

# Timing constants
CYCLE_DURATION = 30 * 60  # 30 minutos en segundos
NIGHT_START_HOUR = 0      # 00:00
NIGHT_END_HOUR = 7        # 07:00
LED_BLINK_INTERVAL = 0.5  # Parpadeo cuando no hay NTP

def log(msg):
    """Log with module prefix"""
    print(f'[heladera] {msg}')
    try:
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except:
        pass

def has_valid_time():
    """
    Verifica si tenemos una hora válida desde NTP.
    MicroPython inicializa con (2000, 1, 1, 0, 0, 0, 5, 1)
    """
    try:
        tm = time.localtime()
        # Si el año es > 2020, asumimos que NTP funcionó
        return tm[0] > 2020
    except Exception as e:
        log(f'Error verificando hora: {e}')
        return False

def is_night_time():
    """
    Verifica si estamos en horario de descanso nocturno (00:00-07:00)
    Retorna True si es de noche, False si es de día
    """
    try:
        tm = time.localtime()
        hour = tm[3]
        # Noche: 00:00-07:00
        return hour >= NIGHT_START_HOUR and hour < NIGHT_END_HOUR
    except Exception as e:
        log(f'Error verificando hora nocturna: {e}')
        return False

def run(cfg):
    """
    Función principal de la app heladera.

    Lógica:
    - Con NTP: ciclo 30min ON/OFF de 07:00-00:00, descanso 00:00-07:00
    - Sin NTP: LED parpadea cada 0.5s, ciclo 30min ON/OFF continuo (sin descanso)
    - LED encendido = app OK, heladera en OFF
    - LED apagado = relé activado, heladera ON
    """
    log('=== Heladera App ===')
    gc.collect()

    try:
        # Inicializar hardware
        relay = machine.Pin(RELAY_PIN, machine.Pin.OUT)
        led = machine.Pin(LED_PIN, machine.Pin.OUT)

        # Relé NC: LOW = heladera ON, HIGH = heladera OFF
        relay.off()  # Iniciar con heladera ON
        led.on()     # LED encendido = app OK

        log('Hardware inicializado')
        log(f'Relay: GPIO{RELAY_PIN} (NC)')
        log(f'LED: GPIO{LED_PIN}')
        gc.collect()

        # Estado del ciclo
        fridge_on = True
        cycle_start = time.time()
        last_blink = time.time()
        led_state = True

        log('Loop principal iniciado')

        while True:
            current_time = time.time()
            has_ntp = has_valid_time()

            # Modo degradado: sin NTP - ciclo continuo sin descanso
            if not has_ntp:
                # Parpadear LED cada 0.5s para indicar sin NTP
                if current_time - last_blink >= LED_BLINK_INTERVAL:
                    led_state = not led_state
                    if led_state:
                        led.on()
                    else:
                        led.off()
                    last_blink = current_time

                # Ciclo 30min ON/OFF sin importar la hora
                elapsed = current_time - cycle_start
                if elapsed >= CYCLE_DURATION:
                    fridge_on = not fridge_on

                    if fridge_on:
                        relay.off()  # NC: LOW = ON
                        log('Sin NTP - Ciclo: Heladera ON (30 min)')
                    else:
                        relay.on()   # NC: HIGH = OFF
                        log('Sin NTP - Ciclo: Heladera OFF (30 min)')

                    cycle_start = current_time
                    gc.collect()

                time.sleep(0.1)
                continue

            # Con NTP: verificar si es de noche
            if is_night_time():
                # Descanso nocturno: apagar heladera
                if fridge_on:
                    relay.on()  # NC: HIGH = OFF
                    led.on()    # LED encendido = heladera apagada
                    fridge_on = False
                    log('Modo nocturno: heladera apagada (00:00-07:00)')

                time.sleep(60)  # Revisar cada minuto
                continue

            # Modo día: ciclo 30min ON/OFF
            elapsed = current_time - cycle_start

            if elapsed >= CYCLE_DURATION:
                # Cambiar estado del ciclo
                fridge_on = not fridge_on

                if fridge_on:
                    relay.off()  # NC: LOW = ON
                    led.off()    # LED apagado = heladera encendida
                    log('Ciclo: Heladera ON (30 min)')
                else:
                    relay.on()   # NC: HIGH = OFF
                    led.on()     # LED encendido = heladera apagada
                    log('Ciclo: Heladera OFF (30 min)')

                cycle_start = current_time
                gc.collect()

            # Esperar un poco antes del siguiente check
            time.sleep(1)

    except KeyboardInterrupt:
        log('Interrumpido por usuario')
        # Apagar heladera y LED al salir
        try:
            relay.on()
            led.off()
        except:
            pass
    except Exception as e:
        log(f'Error: {e}')
        sys.print_exception(e)
