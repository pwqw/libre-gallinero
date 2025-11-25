# main.py - Lógica principal con hotspot fallback
# Lee .env para configuración unificada

try:
    import network
    import ntptime
    import machine
    import dht
    import socket
    import gc
    gc.collect()
except ImportError:
    print("[main] ERROR: Módulos MicroPython no encontrados")

import time
from solar import calc_sun_times
from logic import relay_ponedoras_state, relay_pollitos_state

# Hardware pins (definidos como constantes, inicialización dentro de main())
RELAY1_PIN = 5   # D1 - Ponedoras
RELAY2_PIN = 4   # D2 - Pollitos
DHT_PIN = 14     # D5

# Variables globales para hardware (se inicializan en main())
relay1 = None
relay2 = None
dht_sensor = None

# === CONFIGURACIÓN ===
def parse_env(path):
    """Lee .env"""
    cfg = {}
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    except:
        pass
    return cfg

def load_config():
    """Carga config desde .env con defaults"""
    cfg = parse_env('.env')
    if not cfg:
        cfg = parse_env('.env.example')
    if not cfg:
        cfg = {
            'WIFI_SSID': 'libre gallinero',
            'WIFI_PASSWORD': 'huevos1',
            'WIFI_HIDDEN': 'false',
            'LATITUDE': '-31.4167',
            'LONGITUDE': '-64.1833'
        }
    return cfg

# === HOTSPOT TIME SYNC ===
def hotspot_server():
    """Servidor HTTP para sincronización de hora vía JavaScript"""
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print('[main] HTTP: 192.168.4.1')
    gc.collect()

    while True:
        try:
            cl, _ = s.accept()
            req = cl.recv(1024).decode('utf-8')

            if 'POST /settime' in req:
                parts = req.split('\r\n\r\n', 1)
                body = parts[1] if len(parts) > 1 else ''

                try:
                    # Espera JSON: {"timestamp": 1234567890}
                    import json
                    data = json.loads(body)
                    timestamp = data.get('timestamp')

                    if timestamp:
                        # Convertir timestamp a tupla de tiempo
                        import utime
                        tm = utime.localtime(timestamp)
                        machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
                        print('[main] Hora sincronizada:', tm)
                        cl.send(b'HTTP/1.1 200 OK\r\n\r\n{"status":"ok"}')
                    else:
                        cl.send(b'HTTP/1.1 400\r\n\r\n{"status":"error"}')
                except Exception as e:
                    print('[main] Sync error:', e)
                    cl.send(b'HTTP/1.1 500\r\n\r\n{"status":"error"}')
            else:
                # GET: página con JavaScript para sync (optimizada para memoria)
                h='HTTP/1.1 200 OK\r\nContent-Type:text/html\r\n\r\n'
                h+='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Libre-Gallinero</title></head>'
                h+='<body style="font-family:sans-serif;padding:2em;text-align:center">'
                h+='<h2>Libre-Gallinero</h2><p id="s">Sincronizando hora...</p><script>'
                h+='fetch("/settime",{method:"POST",headers:{"Content-Type":"application/json"},'
                h+='body:JSON.stringify({timestamp:Math.floor(Date.now()/1000)})'
                h+='}).then(r=>r.json()).then(d=>{'
                h+='document.getElementById("s").textContent='
                h+='d.status==="ok"?"Hora sincronizada":"Error";'
                h+='}).catch(()=>{document.getElementById("s").textContent="Error conexión";});'
                h+='</script></body></html>'
                cl.send(h.encode('utf-8'))
                gc.collect()

            cl.close()
        except Exception as e:
            print('[main] HTTP err:', e)
            try:
                cl.close()
            except:
                pass

def start_hotspot(cfg):
    """Crea hotspot para sincronización de hora"""
    ap_ssid = cfg['WIFI_SSID']
    ap_pw = cfg['WIFI_PASSWORD']

    print("[main] Creando hotspot:", ap_ssid)
    gc.collect()

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ap_ssid, password=ap_pw, authmode=3)

    try:
        ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
    except:
        pass

    ip = ap.ifconfig()[0]
    print("[main] Hotspot OK:", ip)
    print("[main] SSID:", ap_ssid)
    print("[main] HTTP Sync: http://", ip, sep='')
    print("[main] WebREPL: ws://", ip, ":8266", sep='')
    print("[main] (WebREPL ya iniciado por boot.py)")
    gc.collect()

    hotspot_server()

# === WIFI + NTP ===
def connect_wifi(cfg):
    """Conecta WiFi"""
    print('[main] Conectando WiFi...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        ssid = cfg['WIFI_SSID']
        pw = cfg['WIFI_PASSWORD']
        hidden = cfg['WIFI_HIDDEN'].lower() == 'true'

        try:
            if hidden:
                wlan.connect(ssid, pw, -1)
            else:
                wlan.connect(ssid, pw)
        except TypeError:
            wlan.connect(ssid, pw)

        timeout = 0
        while not wlan.isconnected() and timeout < 15:
            time.sleep(1)
            timeout += 1

    if wlan.isconnected():
        print('[main] WiFi OK:', wlan.ifconfig()[0])
        return True

    print('[main] WiFi FAIL')
    return False

def sync_ntp():
    """Sincroniza NTP"""
    print('[main] Sincronizando NTP...')
    for i in range(5):
        try:
            ntptime.settime()
            print('[main] NTP OK')
            return True
        except Exception as e:
            print(f'[main] NTP intento {i+1}/5: {e}')
            time.sleep(2)
    print('[main] NTP FAIL')
    return False

def get_local_time(cfg):
    """Hora local ajustada por zona"""
    tm = time.localtime()
    lon = float(cfg.get('LONGITUDE', -60))
    tz = int(round(lon / 15))
    hour = (tm[3] + tz) % 24
    return tm[0], tm[1], tm[2], hour, tm[4]

# === CONTROL RELAYS ===
def control_ponedoras(cfg):
    """Control relay ponedoras (solar)"""
    global relay1
    if relay1 is None:
        return
    year, month, day, hour, minute = get_local_time(cfg)
    lat = float(cfg.get('LATITUDE', -32.5))
    lon = float(cfg.get('LONGITUDE', -60))

    sunrise_summer, sunset_summer = calc_sun_times(year, 12, 21, lat, lon)
    sunrise_today, sunset_today = calc_sun_times(year, month, day, lat, lon)

    now_min = hour * 60 + minute
    sunrise_summer_min = sunrise_summer[0] * 60 + sunrise_summer[1]
    sunrise_today_min = sunrise_today[0] * 60 + sunrise_today[1]
    sunset_today_min = sunset_today[0] * 60 + sunset_today[1]
    sunset_summer_min = sunset_summer[0] * 60 + sunset_summer[1]

    estado = relay_ponedoras_state(now_min, sunrise_summer_min, sunrise_today_min, sunset_today_min, sunset_summer_min)
    relay1.value(estado)
    print(f'[R1] now={now_min}, estado={estado}')

def control_pollitos():
    """Control relay pollitos (temperatura)"""
    global dht_sensor, relay2
    if dht_sensor is None or relay2 is None:
        return
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        estado = relay_pollitos_state(temp)
        relay2.value(estado)
        print(f'[R2] temp={temp}°C, estado={estado}')
    except Exception as e:
        print('[R2] DHT error:', e)

# === MAIN LOOP ===
def main():
    """Función principal - DEBE ejecutarse manualmente vía WebREPL: import main"""
    global relay1, relay2, dht_sensor
    
    print('\n=== main.py ===')
    gc.collect()
    
    # Inicializar hardware DENTRO de main() para ahorrar memoria
    try:
        relay1 = machine.Pin(RELAY1_PIN, machine.Pin.OUT)
        relay2 = machine.Pin(RELAY2_PIN, machine.Pin.OUT)
        print('[main] Relays inicializados')
        gc.collect()
    except Exception as e:
        print('[main] Error inicializando relays:', e)
        relay1 = None
        relay2 = None
    
    # Inicializar DHT con protección (puede no estar conectado)
    try:
        dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))
        print('[main] DHT inicializado')
        gc.collect()
    except Exception as e:
        print('[main] DHT no disponible (continuando sin sensor):', e)
        dht_sensor = None
        gc.collect()
    
    cfg = load_config()
    print('[main] Config:', cfg.get('WIFI_SSID'))
    gc.collect()

    if not connect_wifi(cfg):
        print('[main] Iniciando hotspot...')
        gc.collect()
        start_hotspot(cfg)
        return

    if not sync_ntp():
        print('[main] Sin NTP, reloj puede estar mal')
    gc.collect()

    print('[main] Loop principal...')
    while True:
        control_ponedoras(cfg)
        control_pollitos()
        gc.collect()
        time.sleep(30)

# IMPORTANTE: main.py NO se ejecuta automáticamente
# Para iniciar manualmente vía WebREPL:
#   >>> import main
#   >>> main.main()
# O simplemente:
#   >>> from main import main; main()
#
# Esto garantiza que WebREPL siempre esté disponible después de boot.py
